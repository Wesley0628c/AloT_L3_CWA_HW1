import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
load_dotenv(ROOT / 'backend' / '.env')

class Settings:
    CWA_API_KEY = os.getenv('CWA_API_KEY', '')
    CWA_DATASET_URL = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001'
    CWA_BUREAU_DATASET_URL = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001'
    FORECAST_URL = 'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-C0032-003'
    CACHE_TTL_SECONDS = max(60, int(os.getenv('CACHE_TTL_SECONDS', '600')))
    DATABASE_PATH = os.getenv('DATABASE_PATH', str(ROOT / 'backend' / 'data.db'))
    WINDY_API_KEY = os.getenv('WINDY_API_KEY', '')
    BACKGROUND_REFRESH = os.getenv('BACKGROUND_REFRESH', 'true').lower() == 'true'

settings = Settings()
