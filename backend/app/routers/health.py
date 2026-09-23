import time
from fastapi import APIRouter
from app.config import settings
from app import database
from app.services.temperature_service import temperature_service

router = APIRouter(prefix='/api/health', tags=['health'])

@router.get('')
def health():
    ts = temperature_service._cache_timestamp
    fresh = bool(ts) and time.time()-ts < settings.CACHE_TTL_SECONDS and not temperature_service._failed
    return {'status': 'ok', 'api_key_configured': bool(settings.CWA_API_KEY),
            'cwa_cache_status': 'fresh' if fresh else 'stale' if ts else 'uninitialized',
            'cached_stations_count': len(temperature_service._cache_data),
            'forecast_updated_at': database.forecast_updated_at()}
