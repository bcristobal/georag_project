-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla para almacenar los metadatos a nivel de Colección (ej. Sentinel-2, HLS)
CREATE TABLE IF NOT EXISTS Collection (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id text UNIQUE NOT NULL, 
    title text,
    description text,
    keywords text[],
    license text,
    providers jsonb DEFAULT '[]'::jsonb,
    semantic_text text, -- Guardamos el texto base del embedding para debug
    embedding vector(768) -- Ajusta esta dimensión según tu modelo de Ollama (ej. nomic-embed-text es 768)
);

-- Tabla para almacenar los Items individuales (las imágenes/mosaicos)
CREATE TABLE IF NOT EXISTS Item (
    item_id text PRIMARY KEY,
    collection_id text REFERENCES Collection(collection_id) ON DELETE CASCADE,
    
    -- Filtros Duros (SQL)
    datetime timestamp with time zone,
    grid_code text,
    gsd numeric,
    processing_level text,
    
    -- Filtros Espaciales (PostGIS)
    geometry geometry(Geometry, 4326),
    bbox geometry(Polygon, 4326),
    
    -- Carga Útil (Los links de descarga directos de los assets)
    assets_urls jsonb DEFAULT '{}'::jsonb,
    
    -- Espacio Semántico (PGVector)
    semantic_text text,
    embedding vector(768) -- Ajusta esta dimensión igual que arriba
);

-- Índices Vectoriales (HNSW para búsqueda de similitud aproximada ultra rápida)
CREATE INDEX IF NOT EXISTS idx_col_embed ON Collection USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_item_embed ON Item USING hnsw (embedding vector_cosine_ops);

-- Índices Espaciales y Temporales
CREATE INDEX IF NOT EXISTS idx_item_geom ON Item USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_item_bbox ON Item USING GIST (bbox);
CREATE INDEX IF NOT EXISTS idx_item_datetime ON Item (datetime);
CREATE INDEX IF NOT EXISTS idx_item_grid ON Item (grid_code);