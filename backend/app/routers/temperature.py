from fastapi import APIRouter, HTTPException, Query
from app.services.temperature_service import temperature_service

router = APIRouter(prefix="/api/temperature", tags=["temperature"])

@router.get("/latest")
async def get_latest_temperature(refresh: bool = Query(False, description="Force refresh cache from CWA API")):
    """
    Get latest CWA station temperature observations.
    """
    data = await temperature_service.get_latest_stations(force_refresh=refresh)
    if not data or not data.get("stations"):
        raise HTTPException(status_code=503, detail="Unable to fetch CWA temperature data")
    return data

@router.get("/geojson")
async def get_temperature_geojson():
    """
    Get latest CWA station temperature data formatted as GeoJSON for Leaflet overlay.
    """
    return await temperature_service.get_geojson()

@router.get("/stations/{station_id}")
async def get_station_detail(station_id: str):
    """
    Get temperature details for a specific weather station.
    """
    data = await temperature_service.get_latest_stations()
    stations = data.get("stations", [])
    for st in stations:
        if st["station_id"].lower() == station_id.lower():
            return st
    raise HTTPException(status_code=404, detail=f"Station ID '{station_id}' not found")
