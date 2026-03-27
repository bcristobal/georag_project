import geopandas as gpd
from shapely.geometry import shape

class EnriquecedorADM2:
    def __init__(self, ruta_shapefile: str):
        print(f"Cargando mapa mundial en memoria ({ruta_shapefile})... Esto tomará unos segundos.")
        # geopandas lee automáticamente el .shp y saca los nombres del .dbf
        self.gdf_fronteras = gpd.read_file(ruta_shapefile)
        print("¡Mapa global ADM2 cargado con éxito!")

    def obtener_regiones(self, item_geojson_dict: dict) -> list:
        """
        Cruza la geometría de un item STAC con los regions del mundo en milisegundos.
        """
        # Convertimos el dict del STAC a una geometría de Shapely
        tile_shape = shape(item_geojson_dict)
        
        # MAGIA DE GEOPANDAS: 
        # Esto usa un índice espacial en C por debajo. Filtra el mundo entero en milisegundos.
        intersecciones = self.gdf_fronteras[self.gdf_fronteras.geometry.intersects(tile_shape)]
        
        if intersecciones.empty:
            return []
            
        resultados = []
        # Iteramos solo sobre los pocos regions que han dado positivo
        for idx, fila in intersecciones.iterrows():
            # geoBoundaries suele usar "shapeName" para la región y "shapeGroup" para el país
            region = fila.get('shapeName', 'Desconocido')
            pais = fila.get('shapeGroup', 'Desconocido')
            
            # Calculamos el área para ordenar por importancia
            area = tile_shape.intersection(fila.geometry).area
            
            resultados.append({
                "texto": f"{region} ({pais})",
                "peso": area
            })
            
        # Devolvemos la lista ordenada por el área ocupada
        resultados.sort(key=lambda x: x["peso"], reverse=True)
        return [r["texto"] for r in resultados]

# --- Ejemplo de uso en tu pipeline ---
# Instancias esto UNA SOLA VEZ al iniciar tu app/pipeline
# enricher = EnriquecedorADM2("ruta/a/descargas/geoBoundariesCGAZ_ADM2.shp")

# Y para cada tile de tu STAC Crawler:
# mi_tile_geom = feature.get("geometry")
# etiquetas = enricher.obtener_regions(mi_tile_geom)
# print(etiquetas) # ['Vitoria-Gasteiz (Spain)', 'Arratzua-Ubarrundia (Spain)', ...]