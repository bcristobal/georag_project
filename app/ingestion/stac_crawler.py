import json
import time
import os
from calendar import monthrange
from pystac_client.stac_api_io import StacApiIO
from pystac_client.client import Client
from pystac_client.exceptions import APIError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class STACCrawler:
    def __init__(self, catalog_url: str):
        self.catalog_url = catalog_url
        self.client = self._setup_stac_client()

    def _setup_stac_client(self) -> Client:
        retries = Retry(total=8, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
        stac_api_io = StacApiIO()
        stac_api_io.session.mount("https://", HTTPAdapter(max_retries=retries))
        return Client.open(self.catalog_url, stac_io=stac_api_io)

    # ... (Mantén los métodos estáticos _get_monthly_intervals, _split_bbox_in_two y _save_features igual) ...
    @staticmethod
    def _get_monthly_intervals(start_year: int, end_year: int):
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                last_day = monthrange(year, month)[1]
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day}"
                yield year, month, f"{start_date}T00:00:00Z/{end_date}T23:59:59Z"

    @staticmethod
    def _split_bbox_in_two(bbox: list) -> list:
        min_lon, min_lat, max_lon, max_lat = bbox
        mid_lon = (min_lon + max_lon) / 2.0
        return [[min_lon, min_lat, mid_lon, max_lat], [mid_lon, min_lat, max_lon, max_lat]]

    @staticmethod
    def _save_features(items: list, filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "type": "FeatureCollection",
                "features": items
            }, f, indent=2, ensure_ascii=False)

    # NUEVO MÉTODO PARA DESCARGAR LA COLECCIÓN
    def download_collection(self, collection_id: str, output_dir: str) -> str:
        """Descarga y guarda los metadatos de la colección en sí."""
        os.makedirs(output_dir, exist_ok=True)
        print(f"Obteniendo metadatos de la colección: {collection_id}...")
        
        collection = self.client.get_collection(collection_id)
        collection_dict = collection.to_dict()
        
        filename = os.path.join(output_dir, f"{collection_id}_metadata.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(collection_dict, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Colección guardada en {filename}")
        return filename

    def download_items(self, collection_id: str, bbox: list, start_year: int, end_year: int, output_dir: str) -> str:
        """Descarga progresiva dividiendo por espacio y tiempo."""
        os.makedirs(output_dir, exist_ok=True)
        all_items = []
        sub_bboxes = self._split_bbox_in_two(bbox)
        
        print(f"Iniciando descarga de items para {collection_id}...")
        
        for i, current_bbox in enumerate(sub_bboxes):
            region_name = "Oeste" if i == 0 else "Este"
            print(f"\n--- Procesando Región {region_name} ({i+1}/2) ---")
            
            for year, month, datetime_interval in self._get_monthly_intervals(start_year, end_year):
                print(f"  Consultando: {year}-{month:02d}...")
                
                max_intentos = 3
                for intento in range(max_intentos):
                    try:
                        search = self.client.search(
                            collections=[collection_id],
                            bbox=current_bbox, 
                            datetime=datetime_interval,
                            limit=100
                        )
                        
                        items_mes_region = [item.to_dict() for page in search.pages() for item in page.items]
                        
                        if items_mes_region:
                            all_items.extend(items_mes_region)
                            mes_filename = os.path.join(output_dir, f"{collection_id}_{region_name}_{year}_{month:02d}.json")
                            self._save_features(items_mes_region, mes_filename)
                        
                        time.sleep(3) 
                        break 
                        
                    except APIError as e:
                        if "429" in str(e):
                            espera = (intento + 1) * 60
                            print(f"    [!] WAF detectado. Esperando {espera}s...")
                            time.sleep(espera)
                        else:
                            raise e
                else:
                    print(f"  ❌ Imposible descargar {year}-{month:02d} tras varios intentos.")

        if all_items:
            final_filename = os.path.join(output_dir, f"{collection_id}_completos.json")
            self._save_features(all_items, final_filename)
            print(f"\n✅ Guardados {len(all_items)} items en {final_filename}")
            return final_filename
        return ""