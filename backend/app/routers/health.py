from fastapi import APIRouter
from datetime import datetime
from app.services.temperature_service import temperature_service

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("")
async def health_check():
    """
    Health check endpoint.
    """
    cache_ts = temperature_service._cache_timestamp
    cached_time = datetime.fromtimestamp(cache_ts).isoformat() if cache_ts > 0 else None

    return {
        "status": "ok",
        "service": "CWA Temperature Broadcast API",
        "cwa_cache_status": "fresh" if cache_ts > 0 else "uninitialized",
        "latest_cache_time": cached_time,
        "cached_stations_count": len(temperature_service._cache_data)
    }
