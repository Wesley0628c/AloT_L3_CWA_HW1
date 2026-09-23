import os
from pathlib import Path
from dotenv import load_dotenv
from app.sources import SOURCES

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')

class Settings:
    CWA_API_KEY = os.getenv('CWA_API_KEY', '')
    CWA_DATASET_URL = SOURCES['automatic']['url']
    CWA_BUREAU_DATASET_URL = SOURCES['bureau']['url']
    FORECAST_URL = SOURCES['forecast']['url']
    CACHE_TTL_SECONDS = max(60, int(os.getenv('CACHE_TTL_SECONDS', '600')))
    DATABASE_PATH = os.getenv('DATABASE_PATH', str(ROOT / 'data' / 'weather.db'))
    BACKGROUND_REFRESH = os.getenv('BACKGROUND_REFRESH', 'true').lower() == 'true'

settings = Settings()
