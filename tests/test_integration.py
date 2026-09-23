import asyncio
import csv
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app import database
from app.config import settings
from app.main import app
from app.services.cwa_client import cwa_client
from app.services.weather_service import weather_service
from app.services.forecast_service import ForecastService, forecast_service, parse_forecasts, records_csv
from app.services.temperature_service import TemperatureService, temperature_service, parse_float


def raw_forecast(days=7):
    return {'cwaopendata': {'Dataset': {'Locations': {'Location': [
        {'LocationName': region, 'WeatherElement': [
            {'ElementName': label, 'Time': [
                {'StartTime': (database.today()+timedelta(days=i)).isoformat()+'T06:00:00+08:00',
                 'ElementValue': {key: value}}
                for i in range(days)]}
            for label,key,value in [('最低溫度','MinTemperature','0'),('最高溫度','MaxTemperature','30')]]}
        for region in database.REGIONS]}}}}


def raw_station(temp=28, name='測試站', observed=None):
    return {'StationId':'C0001', 'StationName':name,
            'GeoInfo':{'CountyName':'臺北市','TownName':'中正區','Coordinates':[{'CoordinateName':'WGS84','StationLatitude':'25','StationLongitude':'121'}]},
            'ObsTime':{'DateTime':observed or datetime.now(timezone.utc).isoformat()},
            'WeatherElement':{'AirTemperature':temp,'RelativeHumidity':'80','WindSpeed':'2','Now':{'Precipitation':'0'}}}




def test_forecast_parser_zero_duplicates_and_missing_values():
    raw=raw_forecast()
    periods=raw['cwaopendata']['Dataset']['Locations']['Location'][0]['WeatherElement'][0]['Time']
    periods.append({**periods[0], 'ElementValue':{'MinTemperature':'-2'}})
    parsed=parse_forecasts(raw)
    assert len(parsed)==42
    assert parsed[0]['minT']==-2
    assert parsed[7]['minT']==0
    periods[1]['ElementValue']['MinTemperature']='-99'
    assert len(parse_forecasts(raw))==41


def test_forecasts_only_current_seven_days_and_replace():
    now=datetime.now(timezone.utc).isoformat()
    records=parse_forecasts(raw_forecast(9))
    records.append({**records[0], 'dataDate':(database.today()-timedelta(days=1)).isoformat()})
    database.save_forecasts(records,now)
    assert len(database.get_regional_forecasts())==42
    assert len(database.get_regional_forecasts('中部地區'))==7
    database.save_forecasts(records[:7],now)
    assert len(database.get_regional_forecasts())==7


def test_refresh_failure_preserves_original_timestamp(monkeypatch):
    service=ForecastService()
    async def good(*args): return raw_forecast()
    monkeypatch.setattr(cwa_client,'fetch_json',good)
    first=asyncio.run(service.get(force=True))
    assert first['count']==42 and not first['stale']
    async def bad(*args): return {'invalid':'data'}
    monkeypatch.setattr(cwa_client,'fetch_json',bad)
    second=asyncio.run(service.get(force=True))
    assert second['stale'] and second['count']==42
    assert second['updated_at']==first['updated_at']


def test_incomplete_region_refresh_cannot_replace_complete_cache(monkeypatch):
    database.save_forecasts(parse_forecasts(raw_forecast()),datetime.now(timezone.utc).isoformat())
    payload=raw_forecast()
    payload['cwaopendata']['Dataset']['Locations']['Location'].pop()
    async def incomplete(*args): return payload
    monkeypatch.setattr(cwa_client,'fetch_json',incomplete)
    result=asyncio.run(ForecastService().get(force=True))
    assert result['count']==42 and result['stale']


@pytest.mark.parametrize('value',[-99,-999,'NaN','Infinity',None,'X',{}])
def test_invalid_station_numbers(value):
    assert parse_float(value) is None


def test_station_validation_and_observation_time():
    service=TemperatureService()
    assert service._parse_station(raw_station(temp=51)) is None
    assert service._parse_station(raw_station(observed='bad date')) is None
    assert service._parse_station(raw_station(temp=0))['temperature_c']==0
    invalid=raw_station();invalid['GeoInfo']['Coordinates'][0]['StationLatitude']='999'
    assert service._parse_station(invalid) is None


def test_station_fallback_survives_restart_and_is_marked_stale(monkeypatch):
    service=TemperatureService()
    async def good(): return [raw_station()]
    monkeypatch.setattr(cwa_client,'fetch_automatic_stations',good)
    first=asyncio.run(service.get_latest_stations(True))
    assert first['count']==1 and first['partial']
    restored=asyncio.run(TemperatureService().get_latest_stations())
    assert restored['partial'] and restored['updated_at']==first['updated_at']
    async def bad(): return []
    monkeypatch.setattr(cwa_client,'fetch_automatic_stations',bad)
    second=asyncio.run(TemperatureService().get_latest_stations(True))
    assert second['stale'] and second['count']==1
    assert second['updated_at']==first['updated_at']
    assert len(database.list_snapshots())==1


def test_snapshot_retention():
    old=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()
    current=datetime.now(timezone.utc).isoformat()
    database.save_snapshot([],old)
    database.save_snapshot([{'station_id':'test'}],current)
    assert database.list_snapshots()==[{'captured_at':current,'count':1}]
    assert database.get_snapshot(current)['stations'][0]['station_id']=='test'


def test_csv_quotes_unicode_and_formula_escaping():
    content=records_csv([{'name':'測站,"一"\n新行','value':'=SUM(1,2)'}],['name','value'])
    rows=list(csv.DictReader(io.StringIO(content.lstrip('\ufeff'))))
    assert rows[0]['name']=='測站,"一"\n新行'
    assert rows[0]['value'].startswith("'=")


def test_sql_readonly_and_parameterized_region():
    database.save_forecasts(parse_forecasts(raw_forecast()),datetime.now(timezone.utc).isoformat())
    assert database.get_regional_forecasts("' OR 1=1 --")==[]
    assert len(database.execute_raw_sql('SELECT * FROM WeeklyForecasts'))==42
    for query in ['DELETE FROM WeeklyForecasts','PRAGMA writable_schema=ON','SELECT 1; DELETE FROM WeeklyForecasts']:
        with pytest.raises(Exception): database.execute_raw_sql(query)
    with pytest.raises(Exception):
        database.execute_raw_sql('SELECT sum(x) FROM (WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT x FROM n)')
    assert len(database.get_regional_forecasts())==42


def test_http_routes_static_exports_geojson_history_and_error_states(monkeypatch):
    async def forecast(*args): return raw_forecast()
    async def stations(): return [raw_station()]
    monkeypatch.setattr(cwa_client,'fetch_json',forecast)
    monkeypatch.setattr(cwa_client,'fetch_automatic_stations',stations)
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        assert '台灣即時氣象' in client.get('/').text
        assert client.get('/js/app.js').status_code==200
        assert len(client.get('/api/forecasts/regions').json()['regions'])==6
        data=client.get('/api/forecasts/chart?region=中部地區').json()
        assert data['count']==7 and not data['stale']
        assert client.get('/api/forecasts/chart?region=invalid').status_code==400
        assert len(list(csv.DictReader(io.StringIO(client.get('/api/forecasts/export/csv').text.lstrip('\ufeff')))))==42
        assert client.get('/api/temperature/latest').json()['count']==1
        geo=client.get('/api/temperature/geojson').json()
        assert geo['features'][0]['geometry']['coordinates']==[121,25]
        assert client.get('/api/temperature/stations/c0001').status_code==200
        assert client.get('/api/temperature/stations/absent').status_code==404
        assert '測試站' in client.get('/api/temperature/export/csv').text
        snapshots=client.get('/api/temperature/history').json()['snapshots']
        assert client.get('/api/temperature/snapshot',params={'at':snapshots[0]['captured_at']}).json()['historical']
        assert client.get('/api/temperature/snapshot?at=absent').status_code==404
        assert client.get('/api/forecasts/sql-query',params={'query':'DROP TABLE WeeklyForecasts'}).status_code==400
        assert 'CWA_API_KEY' not in client.get('/api/weather/capabilities').text
        assert client.get('/api/health').status_code==200


def test_empty_startup_is_honest():
    with TestClient(app) as client:
        assert client.get('/api/temperature/latest').status_code==503
        result=client.get('/api/forecasts/chart').json()
        assert result['count']==0 and result['stale']
        assert client.get('/api/health').json()['cwa_cache_status']=='uninitialized'


def test_concurrent_forecast_requests_share_one_refresh(monkeypatch):
    calls=[]
    async def fetch(*args):
        calls.append(1)
        await asyncio.sleep(0.01)
        return raw_forecast()
    monkeypatch.setattr(cwa_client,'fetch_json',fetch)
    async def run():
        service=ForecastService()
        return await asyncio.gather(*(service.get() for _ in range(5)))
    results=asyncio.run(run())
    assert len(calls)==1
    assert all(r['count']==42 for r in results)


def test_background_refresh_runs_both_sources_and_survives_failure(monkeypatch):
    from app.main import refresh_loop
    calls=[]
    async def observations(force_refresh=False):
        calls.append(('stations',force_refresh))
        raise ValueError('simulated upstream failure')
    async def forecasts(force=False):
        calls.append(('forecast',force))
    async def stop_after_cycle(seconds):
        calls.append(('sleep',seconds))
        raise asyncio.CancelledError()
    monkeypatch.setattr(temperature_service,'get_latest_stations',observations)
    monkeypatch.setattr(forecast_service,'refresh',forecasts)
    monkeypatch.setattr(asyncio,'sleep',stop_after_cycle)
    async def product(name): return {'available':False}
    monkeypatch.setattr(weather_service,'get',product)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(refresh_loop())
    assert calls==[('stations',True),('forecast',True),('sleep',settings.CACHE_TTL_SECONDS)]


def test_invalid_wind_direction_and_trace_rain_are_not_real_measurements():
    raw=raw_station()
    raw['WeatherElement']['WindDirection']='-990'
    raw['WeatherElement']['Now']['Precipitation']='-998'
    parsed=TemperatureService()._parse_station(raw)
    assert parsed['wind_direction_deg'] is None
    assert parsed['precipitation_mm'] is None
