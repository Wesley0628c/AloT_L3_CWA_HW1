import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
from app import database
from app.config import settings
from app.services.cwa_client import cwa_client
from app.services.forecast_service import forecast_service
from app.services.temperature_service import temperature_service
from app.services.weather_service import weather_service

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(database,'DB_PATH',str(tmp_path/'test.db'))
    monkeypatch.setattr(settings,'BACKGROUND_REFRESH',False)
    database.init_database()
    async def nothing(*args, **kwargs): return None
    async def empty(*args, **kwargs): return []
    monkeypatch.setattr(cwa_client,'fetch_json',nothing)
    monkeypatch.setattr(cwa_client,'fetch_automatic_stations',empty)
    monkeypatch.setattr(cwa_client,'fetch_bureau_stations',empty)
    temperature_service.__init__()
    forecast_service.__init__()
    weather_service.__init__()
    async def unavailable(name): raise ValueError("offline test")
    monkeypatch.setattr(weather_service, "fetch", unavailable)
