from fastapi import APIRouter, HTTPException, Query, Response
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

@router.get("/export/csv")
async def export_temperature_csv():
    """
    Export all station temperature data as downloadable CSV.
    """
    csv_data = await temperature_service.export_csv()
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=cwa_temperatures.csv"})

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


@router.get('/history')
def history():
    from app.database import list_snapshots
    return {'snapshots': list_snapshots(), 'retention_days': 7}

@router.get('/snapshot')
def snapshot(at: str):
    from app.database import get_snapshot
    data = get_snapshot(at)
    if not data:
        raise HTTPException(404, '找不到此觀測快照')
    return {**data, 'historical': True}
