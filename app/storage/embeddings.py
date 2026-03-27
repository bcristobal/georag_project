import os
from dotenv import load_dotenv
from ollama import Client

def build_collection_semantic_text(collection_data: dict) -> str:
    """Extrae y limpia solo el texto útil para el motor semántico."""
    title = collection_data.get('title', '')
    desc = collection_data.get('description', '')
    keywords = ", ".join(collection_data.get('keywords', []))
    
    return f"Title: {title}. Description: {desc}. Keywords: {keywords}."

def build_item_semantic_text(item_data: dict, collection_title: str = "Sentinel-2", regiones: list = None) -> str:
    """Genera contexto semántico conciso para un item individual, incluyendo regiones."""
    props = item_data.get('properties', {})
    grid = props.get('grid:code', 'Unknown')
    instruments = ", ".join(props.get('instruments', []))
    
    texto_base = f"Satellite image from {collection_title}. Grid tile {grid} captured using {instruments} instruments."
    
    if regiones:
        # Extraemos el texto a partir de los diccionarios
        texto_regiones = ", ".join([f"{r['region']} ({r['pais']})" for r in regiones])
        texto_base += f" Covers regions: {texto_regiones}."
        
    return texto_base

class OllamaEmbedder:
    """Cliente ligero para generar embeddings locales sin dependencias de PyTorch/HF."""
    
    def __init__(self, model_name: str = 'nomic-embed-text-v2-moe:latest'):
        load_dotenv()
        self.model_name = model_name
        self.client = Client(host=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))

    def embed(self, text: str) -> list[float]:
        """Devuelve el vector de un texto dado."""
        response = self.client.embed(
            model=self.model_name,
            input=text
        )
        return response["embeddings"][0]