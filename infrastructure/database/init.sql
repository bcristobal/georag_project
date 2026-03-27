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
    
    -- Eliminamos el array 'regions' de aquí
);

CREATE TABLE IF NOT EXISTS Country (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS Region (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    country_id uuid REFERENCES Country(id) ON DELETE CASCADE,
    name text NOT NULL,
    UNIQUE(name, country_id) -- Evita duplicados de la misma región en el mismo país
);

-- NUEVA TABLA INTERMEDIA: Relación estricta muchos a muchos
CREATE TABLE IF NOT EXISTS Item_Region (
    item_id text REFERENCES Item(item_id) ON DELETE CASCADE,
    region_id uuid REFERENCES Region(id) ON DELETE CASCADE,
    PRIMARY KEY (item_id, region_id)
);

-- Índices Vectoriales (HNSW para búsqueda de similitud aproximada ultra rápida)
CREATE INDEX IF NOT EXISTS idx_col_embed ON Collection USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_item_embed ON Item USING hnsw (embedding vector_cosine_ops);

-- Índices Espaciales y Temporales
CREATE INDEX IF NOT EXISTS idx_item_geom ON Item USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_item_bbox ON Item USING GIST (bbox);
CREATE INDEX IF NOT EXISTS idx_item_datetime ON Item (datetime);
CREATE INDEX IF NOT EXISTS idx_item_grid ON Item (grid_code);

-- Índice adicional recomendado para la tabla intermedia (Optimiza las búsquedas inversas)
CREATE INDEX IF NOT EXISTS idx_item_region_region_id ON Item_Region (region_id);