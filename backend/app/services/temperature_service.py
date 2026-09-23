import asyncio
import math
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.services.cwa_client import cwa_client
from app.config import settings
from app import database
from app.services.forecast_service import records_csv

logger = logging.getLogger(__name__)

INVALID_VALUES = {"", "X", "NA", "null", None, "-99", "-999", "-99.0", "-999.0"}

def parse_float(val: Any) -> Optional[float]:
    if val is None or str(val) in INVALID_VALUES:
        return None
    try:
        f = float(val)
        return f if math.isfinite(f) and f not in (-99.0, -999.0) else None
    except (ValueError, TypeError):
        return None

def parse_datetime(val):
    try:
        result = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
        return result if result.tzinfo else result.replace(tzinfo=database.TAIPEI)
    except (TypeError, ValueError):
        return None

class TemperatureService:
    def __init__(self):
        self._cache_data = []
        self._cache_timestamp = 0
        self._cache_ttl = settings.CACHE_TTL_SECONDS
        self._last_attempt = 0
        self._failed = False
        self._partial = False
        self._lock = None

    async def get_latest_stations(self, force_refresh=False):
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            now = time.time()
            if not self._cache_data:
                saved = database.get_snapshot()
                if saved:
                    self._cache_data = saved['stations']
                    self._partial = saved['partial']
                    self._cache_timestamp = datetime.fromisoformat(saved['updated_at']).timestamp()
            expired = now - self._cache_timestamp >= self._cache_ttl
            retry_ready = now - self._last_attempt >= 60
            if force_refresh or (expired and retry_ready):
                self._last_attempt = now
                raw_auto, raw_bureau = await asyncio.gather(
                    cwa_client.fetch_automatic_stations(), cwa_client.fetch_bureau_stations())
                parsed = {}
                for raw in raw_auto + raw_bureau:
                    station = self._parse_station(raw)
                    if station:
                        old = parsed.get(station['station_id'])
                        if not old or station['observed_at'] > old['observed_at']:
                            parsed[station['station_id']] = station
                if parsed:
                    self._cache_data = list(parsed.values())
                    self._cache_timestamp = now
                    self._failed = False
                    self._partial = not raw_auto or not raw_bureau
                    database.save_snapshot(self._cache_data, datetime.fromtimestamp(now, timezone.utc).isoformat(), self._partial)
                else:
                    self._failed = True
            outdated = any(now - datetime.fromisoformat(st['observed_at']).timestamp() > 3600 for st in self._cache_data)
            return {
                'source': 'CWA OpenData',
                'updated_at': datetime.fromtimestamp(self._cache_timestamp, timezone.utc).isoformat() if self._cache_timestamp else None,
                'count': len(self._cache_data), 'stations': self._cache_data,
                'stale': self._failed or outdated or now-self._cache_timestamp >= self._cache_ttl,
                'partial': self._partial,
            }

    async def get_geojson(self) -> Dict[str, Any]:
        data = await self.get_latest_stations()
        features = []

        for st in data["stations"]:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [st["lon"], st["lat"]] # GeoJSON format: [lon, lat]
                },
                "properties": {
                    "station_id": st["station_id"],
                    "station_name": st["station_name"],
                    "county": st["county"],
                    "town": st["town"],
                    "temperature_c": st["temperature_c"],
                    "humidity_percent": st["humidity_percent"],
                    "wind_speed_mps": st["wind_speed_mps"],
                    "weather": st["weather"],
                    "observed_at": st["observed_at"]
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }

    async def export_csv(self):
        data = await self.get_latest_stations()
        return records_csv(data['stations'], ['station_id','station_name','county','town','lat','lon',
                            'temperature_c','humidity_percent','wind_speed_mps','precipitation_mm','observed_at'])

    def _parse_station(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            station_id = raw.get("StationId") or raw.get("stationId")
            station_name = raw.get("StationName") or raw.get("locationName")
            if not station_id or not station_name:
                return None

            # Coordinates extraction
            lat, lon = None, None
            geo_info = raw.get("GeoInfo", {})
            coords = geo_info.get("Coordinates", [])

            for c in coords:
                if c.get("CoordinateName") == "WGS84":
                    lat = parse_float(c.get("StationLatitude"))
                    lon = parse_float(c.get("StationLongitude"))
                    break

            if lat is None or lon is None:
                # Fallback to direct fields
                lat = parse_float(raw.get("lat") or geo_info.get("StationLatitude"))
                lon = parse_float(raw.get("lon") or geo_info.get("StationLongitude"))

            if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return None

            # Temperature extraction & validation
            weather_elem = raw.get("WeatherElement", {})
            temp_c = parse_float(weather_elem.get("AirTemperature"))

            # Validation Rule: ignore if temp is missing or out of [-20, 50] range
            if temp_c is None or not (-20.0 <= temp_c <= 50.0):
                return None

            obs_time = parse_datetime(raw.get("ObsTime", {}).get("DateTime"))
            if obs_time is None:
                return None
            county = geo_info.get("CountyName") or raw.get("parameter", [{}])[0].get("parameterValue")
            town = geo_info.get("TownName")

            humidity = parse_float(weather_elem.get("RelativeHumidity"))
            if humidity is not None and not 0 <= humidity <= 100:
                humidity = None
            pressure = parse_float(weather_elem.get("AirPressure"))
            wind_speed = parse_float(weather_elem.get("WindSpeed"))
            if wind_speed is not None and wind_speed < 0:
                wind_speed = None
            wind_dir = parse_float(weather_elem.get("WindDirection"))

            precip = parse_float(weather_elem.get("Now", {}).get("Precipitation"))
            weather_str = weather_elem.get("Weather")

            return {
                "station_id": str(station_id),
                "station_name": str(station_name),
                "county": county,
                "town": town,
                "lat": lat,
                "lon": lon,
                "altitude_m": parse_float(geo_info.get("StationAltitude")),
                "observed_at": obs_time.isoformat(),
                "temperature_c": temp_c,
                "humidity_percent": humidity,
                "pressure_hpa": pressure,
                "wind_speed_mps": wind_speed,
                "wind_direction_deg": wind_dir,
                "precipitation_mm": precip,
                "weather": weather_str if weather_str is not None and str(weather_str) not in INVALID_VALUES else None
            }
        except Exception as e:
            logger.warning(f"Error parsing station record {raw.get('StationId')}: {e}")
            return None

temperature_service = TemperatureService()
