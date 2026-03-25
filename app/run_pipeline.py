from app.ingestion.stac_crawler import STACCrawler
from app.storage.embeddings import OllamaEmbedder
from app.storage.repository import VectorStorage
from app.ingestion.boundaries import EnriquecedorADM2 # <-- Añadimos esta importación

# 1. Configuración
DSN = "postgresql://admin:password123@localhost:5432/rag_database"
OUTPUT_DIR = "descargas_stac"
COLLECTION_NAME = "sentinel-2-global-mosaics"
# Ruta extraída de tu captura de pantalla
SHP_PATH = "geoBoundariesCGAZ_ADM2/geoBoundariesCGAZ_ADM2.shp"

# Inicializamos los servicios
db = VectorStorage(DSN)
embedder = OllamaEmbedder()
crawler = STACCrawler("https://stac.dataspace.copernicus.eu/v1/")
enricher = EnriquecedorADM2(SHP_PATH) # <-- Cargamos el shapefile en memoria


# 2. Descargar TODOS los metadatos (Colección + Items)
print("\n=== FASE 1: DESCARGA DE METADATOS STAC ===")
ruta_coleccion = crawler.download_collection(COLLECTION_NAME, OUTPUT_DIR)
ruta_items = crawler.download_items(COLLECTION_NAME, [-11.1, 34.7, 4.9, 44.1], 2015, 2015, OUTPUT_DIR)


ruta_items = f"{OUTPUT_DIR}/{COLLECTION_NAME}_completos.json" # Usamos los que ya tienes
ruta_coleccion = f"{OUTPUT_DIR}/{COLLECTION_NAME}_metadata.json" 

# 3. Ingestar datos en Postgres usando Ollama para los vectores
print("\n=== FASE 2: INGESTA EN BASE DE DATOS (PGVECTOR) ===")
print("Inyectando Colección...")
db.insert_collection_from_json(ruta_coleccion, embedding_func=embedder.embed)

print("Inyectando Items y enriqueciendo espacialmente...")
# Pasamos el enricher como parámetro
db.insert_items_from_feature_collection(ruta_items, embedding_func=embedder.embed, enricher=enricher)


# 4. Buscar
print("\n=== FASE 3: PRUEBA DE RETRIEVAL ===")
query_vec = embedder.embed("Buscando imágenes del norte de España")
resultados = db.search_hybrid(query_vec, grid_filter="MGRS-31TFH", limit=2)

for res in resultados:
    item_id, date, urls, dist = res
    print(f"\n[+] Encontrado: {item_id} (Distancia semántica: {dist:.4f})")
    print(f" -> Descargar Banda Roja (B04): {urls.get('B04')}")