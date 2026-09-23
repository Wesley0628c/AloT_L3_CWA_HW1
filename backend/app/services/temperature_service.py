import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.services.cwa_client import cwa_client
from app.config import settings

logger = logging.getLogger(__name__)

INVALID_VALUES = {"", "X", "NA", "null", None, "-99", "-999", "-99.0", "-999.0"}

def parse_float(val: Any) -> Optional[float]:
    if val in INVALID_VALUES:
        return None
    try:
        f = float(val)
        return f if f not in (-99.0, -999.0) else None
    except (ValueError, TypeError):
        return None

def parse_datetime(val: Any) -> datetime:
    if not val or val in INVALID_VALUES:
        return datetime.now()
    try:
        # e.g., "2026-09-23T10:00:00+08:00"
        return datetime.fromisoformat(str(val))
    except Exception:
        return datetime.now()

class TemperatureService:
    def __init__(self):
        self._cache_data: List[Dict[str, Any]] = []
        self._cache_timestamp: float = 0
        self._cache_ttl: int = settings.CACHE_TTL_SECONDS

    async def get_latest_stations(self, force_refresh: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force_refresh and self._cache_data and (now - self._cache_timestamp < self._cache_ttl):
            return {
                "source": "CWA OpenData (Cached)",
                "updated_at": datetime.fromtimestamp(self._cache_timestamp).isoformat(),
                "count": len(self._cache_data),
                "stations": self._cache_data
            }

        # Fetch fresh data from CWA client
        raw_auto = await cwa_client.fetch_automatic_stations()
        raw_bureau = await cwa_client.fetch_bureau_stations()

        all_raw = raw_auto + raw_bureau
        parsed_stations = []
        seen_ids = set()

        for raw in all_raw:
            st = self._parse_station(raw)
            if st and st["station_id"] not in seen_ids:
                seen_ids.add(st["station_id"])
                parsed_stations.append(st)

        if parsed_stations:
            self._cache_data = parsed_stations
            self._cache_timestamp = now

        return {
            "source": "CWA OpenData",
            "updated_at": datetime.now().isoformat(),
            "count": len(self._cache_data),
            "stations": self._cache_data
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

    async def export_csv(self) -> str:
        data = await self.get_latest_stations()
        stations = data.get("stations", [])

        lines = ["station_id,station_name,county,town,lat,lon,temperature_c,humidity_percent,wind_speed_mps,precipitation_mm,observed_at"]
        for st in stations:
            st_id = st.get("station_id", "")
            name = st.get("station_name", "")
            county = st.get("county", "") or ""
            town = st.get("town", "") or ""
            lat = st.get("lat", "")
            lon = st.get("lon", "")
            temp = st.get("temperature_c", "")
            hum = st.get("humidity_percent", "")
            wind = st.get("wind_speed_mps", "")
            precip = st.get("precipitation_mm", "")
            obs = st.get("observed_at", "")

            lines.append(f'"{st_id}","{name}","{county}","{town}",{lat},{lon},{temp},{hum},{wind},{precip},"{obs}"')

        return "\n".join(lines)

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

            if lat is None or lon is None:
                return None

            # Temperature extraction & validation
            weather_elem = raw.get("WeatherElement", {})
            temp_c = parse_float(weather_elem.get("AirTemperature"))

            # Validation Rule: ignore if temp is missing or out of [-20, 50] range
            if temp_c is None or not (-20.0 <= temp_c <= 50.0):
                return None

            obs_time = parse_datetime(raw.get("ObsTime", {}).get("DateTime"))
            county = geo_info.get("CountyName") or raw.get("parameter", [{}])[0].get("parameterValue")
            town = geo_info.get("TownName")

            humidity = parse_float(weather_elem.get("RelativeHumidity"))
            pressure = parse_float(weather_elem.get("AirPressure"))
            wind_speed = parse_float(weather_elem.get("WindSpeed"))
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
                "weather": weather_str if weather_str not in INVALID_VALUES else None
            }
        except Exception as e:
            logger.warning(f"Error parsing station record {raw.get('StationId')}: {e}")
            return None

temperature_service = TemperatureService()
