import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import struct

import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import database
from app.services.products import parse_radar,parse_radar_frames,parse_rainfall,parse_typhoons,parse_warnings
from app.services.weather_service import WeatherService,weather_service
from app.services.wind_service import decode_wind,wind_requests

NOW=datetime(2026,9,23,8,tzinfo=timezone.utc)

def response(records):return {'success':'true','records':records}

def test_rainfall_missing_and_negative_are_not_zero():
    base={'StationId':'R1','StationName':'雨站','ObsTime':{'DateTime':NOW.isoformat()},'GeoInfo':{'Coordinates':[{'CoordinateName':'WGS84','StationLatitude':'25','StationLongitude':'121'}]},'RainfallElement':{'Now':{'Precipitation':'-998'},'Past1hr':{'Precipitation':'0'},'Past24hr':{'Precipitation':'25.5'}}}
    data=parse_rainfall(response({'Station':[base]}))
    assert data['count']==1
    assert data['stations'][0]['precipitation_mm'] is None
    assert data['stations'][0]['rain_1h_mm']==0
    assert data['stations'][0]['rain_24h_mm']==25.5


def test_warning_expiry_and_future_effective_time():
    def warning(start,end):return {'datasetInfo':{'datasetDescription':'強風','validTime':{'startTime':start.isoformat(),'endTime':end.isoformat()}},'contents':{'content':{'contentText':'官方內容'}}}
    data=parse_warnings(response({'record':[warning(NOW-timedelta(hours=1),NOW),warning(NOW+timedelta(hours=1),NOW+timedelta(hours=6))]}),now=NOW)
    assert data['count']==1 and not data['warnings'][0]['active']
    assert parse_warnings(response({'record':[]}),now=NOW)['count']==0
    with pytest.raises(ValueError):parse_warnings({'success':'false'},now=NOW)


def test_typhoon_time_and_probability_radius():
    raw={'CwaTdNo':'29','AnalysisData':{'Fix':[{'DateTime':NOW.isoformat(),'CoordinateLatitude':'16.4','CoordinateLongitude':'137.9','MaxWindSpeed':'15','Pressure':'1004'}]},'ForecastData':{'Fix':[{'InitialTime':NOW.isoformat(),'ForecastHour':'6','CoordinateLatitude':'17','CoordinateLongitude':'136','Radius70PercentProbability':'70','Circle15ms':{'Radius':'100'}}]}}
    payload=response({'TropicalCyclones':{'TropicalCyclone':[raw]}})
    storm=parse_typhoons(payload,now=NOW)['typhoons'][0]
    assert storm['name']=='熱帶性低氣壓 29'
    assert storm['forecast'][0]['time']==(NOW+timedelta(hours=6)).isoformat()
    assert storm['forecast'][0]['uncertainty_km']==70
    assert storm['forecast'][0]['radius_15ms_km']==100
    assert parse_typhoons(payload,now=NOW+timedelta(days=2))['count']==0
    assert parse_typhoons(response({'TropicalCyclones':{'TropicalCyclone':[]}}),now=NOW)['count']==0


def radar_payload(url='https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-A0058-006.png'):
    return {'cwaopendata':{'dataset':{'resource':{'ProductURL':url},'datasetInfo':{'parameterSet':{'LongitudeRange':'118.0-124.0','LatitudeRange':'20.5-26.5'}},'DateTime':NOW.isoformat()}}}


def test_radar_metadata_and_allowed_host():
    data=parse_radar(radar_payload())
    assert data['bounds']==[[20.5,118],[26.5,124]]
    assert data['image_url']=='/api/weather/radar/image'
    for url in ['http://localhost/secret','https://evil.example/radar.png','https://cwaopendata.s3.ap-northeast-1.amazonaws.com/r.png?key=secret']:
        with pytest.raises(ValueError):parse_radar(radar_payload(url))


def test_rainviewer_hash_paths_and_no_active_forecasts():
    data=parse_radar_frames({'host':'https://tilecache.rainviewer.com','radar':{'past':[{'time':int(NOW.timestamp()),'path':'/v2/radar/6a9a1b47a93f'}],'nowcast':[]}})
    assert data['count']==1 and '/6a9a1b47a93f/' in data['frames'][0]['tiles']
    with pytest.raises(ValueError):parse_radar_frames({'host':'https://evil.example','radar':{'past':[]}})
    with pytest.raises(ValueError):parse_radar_frames({'host':'https://tilecache.rainviewer.com','radar':{'past':[{'time':1,'path':'/v2/radar/../../private'}]}})


def test_failed_product_update_survives_restart(monkeypatch):
    service=WeatherService()
    async def good(name):return {'count':0,'warnings':[],'source':'CWA'}
    monkeypatch.setattr(service,'fetch',good)
    first=asyncio.run(service.get('warnings',True))
    assert first['available'] and not first['stale'] and first['count']==0
    restart=WeatherService()
    async def bad(name):raise ValueError('upstream failed')
    monkeypatch.setattr(restart,'fetch',bad)
    second=asyncio.run(restart.get('warnings',True))
    assert second['available'] and second['stale']
    assert second['updated_at']==first['updated_at']


def test_expired_warnings_removed_from_cached_response(monkeypatch):
    timestamp=datetime.now(timezone.utc)
    database.save_product('warnings',{'warnings':[{'ends_at':(timestamp-timedelta(minutes=1)).isoformat(),'starts_at':None}],'count':1},timestamp.isoformat())
    data=asyncio.run(WeatherService().get('warnings'))
    assert data['available'] and data['count']==0


def test_failed_product_without_cache_unavailable(monkeypatch):
    service=WeatherService()
    async def bad(name):raise ValueError('upstream unavailable')
    monkeypatch.setattr(service,'fetch',bad)
    data=asyncio.run(service.get('radar',True))
    assert not data['available'] and data['stale'] and data['updated_at'] is None


def test_grib_decodes_ordered_u_v_grid():
    import eccodes as ec
    blobs=[]
    for name,values in [('10u',[1,2,3,4]),('10v',[-1,-2,-3,-4])]:
        h=ec.codes_grib_new_from_samples('regular_ll_sfc_grib2')
        try:
            for key,value in {'Ni':2,'Nj':2,'latitudeOfFirstGridPointInDegrees':25,'longitudeOfFirstGridPointInDegrees':120,'latitudeOfLastGridPointInDegrees':24,'longitudeOfLastGridPointInDegrees':121,'iDirectionIncrementInDegrees':1,'jDirectionIncrementInDegrees':1,'typeOfLevel':'heightAboveGround','level':10,'shortName':name,'dataDate':20260923,'dataTime':0,'forecastTime':6}.items():ec.codes_set(h,key,value)
            ec.codes_set_values(h,values);blobs.append(ec.codes_get_message(h))
        finally:ec.codes_release(h)
    data=decode_wind(b''.join(blobs))
    assert data['width']==data['height']==2
    assert data['u']==[1,2,3,4] and data['v']==[-1,-2,-3,-4]
    assert data['north']==25 and data['south']==24
    assert data['valid_at']=='2026-09-23T06:00:00+00:00'
    with pytest.raises(ValueError):decode_wind(blobs[0])
    with pytest.raises(ValueError):decode_wind(b'not grib')


def test_gfs_cycle_publication_delay_and_day_rollover():
    queries=list(wind_requests(datetime(2026,9,23,2,tzinfo=timezone.utc)))
    assert queries[0]['dir']=='/gfs.20260922/18/atmos'
    assert queries[0]['file']=='gfs.t18z.pgrb2.0p25.f006'
    assert queries[1]['dir']=='/gfs.20260922/12/atmos'


def test_weather_routes_and_unsupported_endpoint():
    with TestClient(app) as client:
        result=client.get('/api/weather/radar').json()
        assert result['available'] is False
        assert client.get('/api/weather/radar/image').status_code==503
        assert client.get('/api/weather/windy').status_code==404
        capabilities=client.get('/api/weather/capabilities').json()
        assert capabilities['supported']['windy'] is False
        assert all('Authorization' not in value for value in capabilities['map_tiles'].values())
        assert client.get('/api/config').status_code==404


def test_probe_rejects_http_200_error_image():
    import importlib.util
    path=Path(__file__).resolve().parents[1]/'scripts/probe_apis.py'
    spec=importlib.util.spec_from_file_location('probe_apis',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='<html>error</html>'))) as client:
            return await module.probe('dark_map',{'url':'https://example.test/tile','format':'image'},client)
    assert asyncio.run(run())['supported'] is False
