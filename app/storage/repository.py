import json
import psycopg
from psycopg.types.json import Jsonb
from pgvector.psycopg import register_vector
import numpy as np
from typing import Callable, Optional

from app.storage.embeddings import build_collection_semantic_text, build_item_semantic_text

class VectorStorage:
    def __init__(self, dsn: str, embedding_dim: int = 768):
        self.dsn = dsn
        self.embedding_dim = embedding_dim

    def insert_collection_from_json(self, filepath: str, embedding_func: Optional[Callable] = None):
        """Lee un JSON de Colección STAC, destila la info y la inserta."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        semantic_text = build_collection_semantic_text(data)
        vector = embedding_func(semantic_text) if embedding_func else [0.05] * self.embedding_dim

        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            
            params = {
                "collection_id": data.get("id"),
                "title": data.get("title"),
                "description": data.get("description"),
                "keywords": data.get("keywords", []),
                "license": data.get("license"),
                "providers": Jsonb(data.get("providers", [])),
                "semantic_text": semantic_text,
                "embedding": np.array(vector)
            }

            conn.execute("""
                INSERT INTO Collection (
                    collection_id, title, description, keywords, 
                    license, providers, semantic_text, embedding
                ) VALUES (
                    %(collection_id)s, %(title)s, %(description)s, %(keywords)s,
                    %(license)s, %(providers)s, %(semantic_text)s, %(embedding)s
                ) ON CONFLICT (collection_id) DO NOTHING;
            """, params)
            
            conn.commit()
            print(f"Collection '{params['collection_id']}' insertada con éxito.")

    def insert_items_from_feature_collection(self, filepath: str, collection_title: str = "Sentinel-2", embedding_func: Optional[Callable] = None, enricher=None):
        """Lee un JSON FeatureCollection, extrae los enlaces útiles, enriquece espacialmente y carga los items."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        features = data.get("features", [])
        if not features:
            print(f"No se encontraron features en el archivo: {filepath}")
            return

        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            
            for feature in features:
                props = feature.get("properties", {})
                grid_code = props.get("grid:code")
                
                bbox = feature.get("bbox")
                if bbox and len(bbox) == 4:
                    xmin, ymin, xmax, ymax = bbox
                else:
                    xmin = ymin = xmax = ymax = None

                geom_dict = feature.get("geometry")
                geom_str = json.dumps(geom_dict) if geom_dict else None
                
                raw_assets = feature.get("assets", {})
                clean_assets_urls = {}
                for asset_name, asset_data in raw_assets.items():
                    default_href = asset_data.get("href")
                    https_href = asset_data.get("alternate", {}).get("https", {}).get("href")
                    clean_assets_urls[asset_name] = https_href if https_href else default_href

                # --- MAGIA DE ENRIQUECIMIENTO AQUÍ ---
                regiones = []
                if enricher and geom_dict:
                    regiones = enricher.obtener_regiones(geom_dict)
                
                # Construimos el texto semántico con las regiones incluidas
                semantic_text = build_item_semantic_text(feature, collection_title, regiones)
                
                # Generamos el vector
                vector = embedding_func(semantic_text) if embedding_func else [0.05] * self.embedding_dim

                params = {
                    "item_id": feature.get("id"),
                    "collection_id": feature.get("collection"),
                    "datetime": props.get("datetime"),
                    "grid_code": grid_code,
                    "gsd": props.get("gsd"),
                    "processing_level": props.get("processing:level"),
                    "assets_urls": Jsonb(clean_assets_urls),
                    "semantic_text": semantic_text,
                    "geometry": geom_str,
                    "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
                    "embedding": np.array(vector)
                }

                conn.execute("""
                    INSERT INTO Item (
                        item_id, collection_id, datetime, grid_code, gsd, processing_level,
                        geometry, bbox, assets_urls, semantic_text, embedding
                    ) VALUES (
                        %(item_id)s, %(collection_id)s, %(datetime)s::timestamp, %(grid_code)s,
                        %(gsd)s, %(processing_level)s,
                        CASE WHEN %(geometry)s::text IS NOT NULL THEN ST_SetSRID(ST_GeomFromGeoJSON(%(geometry)s::text), 4326) ELSE NULL END,
                        CASE WHEN %(xmin)s::numeric IS NOT NULL THEN ST_MakeEnvelope(%(xmin)s::numeric, %(ymin)s::numeric, %(xmax)s::numeric, %(ymax)s::numeric, 4326) ELSE NULL END,
                        %(assets_urls)s, %(semantic_text)s, %(embedding)s
                    ) ON CONFLICT (item_id) DO NOTHING;
                """, params)
                
                item_id = feature.get("id")

                # 2. Insertamos País, Región y Relación
                if regiones:
                    for r_data in regiones:
                        pais_name = r_data["pais"]
                        region_name = r_data["region"]
                        
                        # Guardar País si no existe
                        conn.execute("""
                            INSERT INTO Country (name) VALUES (%s)
                            ON CONFLICT (name) DO NOTHING;
                        """, (pais_name,))
                        
                        # Recuperar ID del País
                        country_id = conn.execute(
                            "SELECT id FROM Country WHERE name = %s", (pais_name,)
                        ).fetchone()[0]

                        # Guardar Región vinculada al País
                        conn.execute("""
                            INSERT INTO Region (name, country_id) VALUES (%s, %s)
                            ON CONFLICT (name, country_id) DO NOTHING;
                        """, (region_name, country_id))
                        
                        # Recuperar ID de la Región
                        region_id = conn.execute(
                            "SELECT id FROM Region WHERE name = %s AND country_id = %s", 
                            (region_name, country_id)
                        ).fetchone()[0]

                        # Guardar Relación (Item_Region)
                        conn.execute("""
                            INSERT INTO Item_Region (item_id, region_id) 
                            VALUES (%s, %s)
                            ON CONFLICT (item_id, region_id) DO NOTHING;
                        """, (item_id, region_id))

            conn.commit()
            print(f"Se procesaron {len(features)} items correctamente de {filepath}.")

    def search_hybrid(self, query_vector: list[float], grid_filter: str = None, limit: int = 5):
        """Ejemplo de Búsqueda Híbrida: Similitud Vectorial + Filtro SQL (Opcional)."""
        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            
            query = """
                SELECT item_id, datetime, assets_urls, embedding <=> %s AS distance
                FROM Item
            """
            params = [np.array(query_vector)]
            
            if grid_filter:
                query += " WHERE grid_code = %s "
                params.append(grid_filter)
                
            query += " ORDER BY distance ASC LIMIT %s"
            params.append(limit)
            
            records = conn.execute(query, tuple(params)).fetchall()
            return records