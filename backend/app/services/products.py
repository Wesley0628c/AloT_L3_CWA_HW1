"""Normalize CWA products; distinguish no active event from invalid payloads."""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from app import database
from app.sources import RADAR_IMAGE_HOST
from app.services.temperature_service import parse_datetime, parse_float


def as_list(value):
    return value if isinstance(value, list) else [value] if isinstance(value, dict) else []


def records(payload):
    if not isinstance(payload, dict) or str(payload.get('success')).lower() != 'true' or 'records' not in payload:
        raise ValueError('CWA dataset unavailable')
    return payload['records']


def parse_rainfall(payload):
    root = records(payload)
    if 'Station' not in root:
        raise ValueError('Rainfall schema missing')
    stations = []
    for raw in as_list(root['Station']):
        geo = raw.get('GeoInfo', {})
        coord = next((c for c in geo.get('Coordinates', []) if c.get('CoordinateName') == 'WGS84'), {})
        lat, lon = parse_float(coord.get('StationLatitude')), parse_float(coord.get('StationLongitude'))
        observed = parse_datetime(raw.get('ObsTime', {}).get('DateTime'))
        if lat is None or lon is None or not (-90<=lat<=90 and -180<=lon<=180) or observed is None:
            continue
        values = raw.get('RainfallElement', {})
        rain = {}
        for output, period in [('precipitation_mm','Now'),('rain_1h_mm','Past1hr'),('rain_24h_mm','Past24hr')]:
            number = parse_float(values.get(period, {}).get('Precipitation'))
            rain[output] = number if number is not None and number>=0 else None
        if all(v is None for v in rain.values()):
            continue
        stations.append({'station_id':raw.get('StationId'), 'station_name':raw.get('StationName'),
                         'county':geo.get('CountyName'), 'town':geo.get('TownName'),
                         'lat':lat, 'lon':lon, 'observed_at':observed.isoformat(), **rain})
    return {'stations':stations, 'count':len(stations), 'source':'CWA O-A0002-001', 'period':'本日 00:00 起累積雨量'}


def parse_warnings(payload, now=None):
    root = records(payload)
    if 'record' not in root:
        raise ValueError('Warning schema missing')
    now = now or datetime.now(timezone.utc)
    items=[]
    for raw in as_list(root['record']):
        info=raw.get('datasetInfo', {})
        valid=info.get('validTime', {})
        start,end=parse_datetime(valid.get('startTime')),parse_datetime(valid.get('endTime'))
        # Include already issued notices for later today, labelled with their start time.
        if end is None or end<=now:
            continue
        content=raw.get('contents', {}).get('content', {})
        text='\n'.join(c.get('contentText','').strip() for c in as_list(content))
        if not text:
            continue
        items.append({'title':info.get('datasetDescription','天氣特報'), 'text':text,
                      'issued_at':info.get('issueTime'), 'starts_at':start.isoformat() if start else None,
                      'ends_at':end.isoformat(), 'active':start is None or start<=now})
    return {'warnings':items,'count':len(items),'source':'中央氣象署 W-C0033-002'}


def parse_typhoons(payload, now=None):
    root=records(payload)
    if 'TropicalCyclones' not in root and 'tropicalCyclones' not in root:
        raise ValueError('Typhoon schema missing')
    storms=root.get('TropicalCyclones',root.get('tropicalCyclones',{}))
    now=now or datetime.now(timezone.utc)
    def point(raw,forecast=False):
        lat=parse_float(raw.get('CoordinateLatitude'));lon=parse_float(raw.get('CoordinateLongitude'))
        time=parse_datetime(raw.get('InitialTime') if forecast else raw.get('DateTime'))
        if time is None or lat is None or lon is None or not (-90<=lat<=90 and -180<=lon<=180):return None
        if forecast:
            hours=parse_float(raw.get('ForecastHour'))
            if hours is None or not 0<=hours<=240:return None
            time+=timedelta(hours=hours)
        def radius(key):
            obj=raw.get(key,{})
            value=parse_float(obj.get('Radius')) if isinstance(obj,dict) else None
            return value if value is not None and value>=0 else None
        return {'lat':lat,'lon':lon,'time':time.isoformat(),'wind_mps':parse_float(raw.get('MaxWindSpeed')),
                'pressure_hpa':parse_float(raw.get('Pressure')),'forecast':forecast,
                'uncertainty_km':parse_float(raw.get('Radius70PercentProbability')) if forecast else None,
                'radius_15ms_km':radius('Circle15ms'),'radius_25ms_km':radius('Circle25ms')}
    items=[]
    for raw in as_list(storms.get('TropicalCyclone',storms.get('tropicalCyclone',[]))):
        analysis=[p for p in (point(x) for x in as_list(raw.get('AnalysisData',{}).get('Fix'))) if p]
        if not analysis:continue
        analysis.sort(key=lambda x:x['time'])
        # CWA sometimes retains the last product after an event has ended.
        if now-datetime.fromisoformat(analysis[-1]['time'])>timedelta(hours=24):continue
        forecast=[p for p in (point(x,True) for x in as_list(raw.get('ForecastData',{}).get('Fix'))) if p]
        forecast.sort(key=lambda x:x['time'])
        items.append({'name':raw.get('CwaTyphoonName') or raw.get('TyphoonName') or '熱帶性低氣壓 '+str(raw.get('CwaTdNo','')),
                      'analysis':analysis,'forecast':forecast,'current':analysis[-1]})
    return {'typhoons':items,'count':len(items),'source':'中央氣象署 W-C0034-005'}


def parse_radar(payload):
    root=payload.get('cwaopendata', {})
    data=root.get('dataset', {})
    url=data.get('resource',{}).get('ProductURL','')
    parts=urlsplit(url)
    if parts.scheme!='https' or parts.hostname!=RADAR_IMAGE_HOST or parts.query:
        raise ValueError('Unexpected radar image source')
    params=data.get('datasetInfo',{}).get('parameterSet',{})
    try:
        west,east=map(float,params['LongitudeRange'].split('-'))
        south,north=map(float,params['LatitudeRange'].split('-'))
        if not (-180<=west<east<=180 and -90<=south<north<=90):raise ValueError()
    except (KeyError,TypeError,ValueError):
        raise ValueError('Radar bounds missing') from None
    observed=parse_datetime(data.get('DateTime'))
    if observed is None:raise ValueError('Radar timestamp missing')
    return {'image_source':url,'image_url':'/api/weather/radar/image','bounds':[[south,west],[north,east]],
            'observed_at':observed.isoformat(),'source':'中央氣象署 O-A0058-006'}


def parse_radar_frames(payload):
    # The public timeline is optional; do not accept arbitrary tile hosts from an upstream JSON.
    if payload.get('host')!='https://tilecache.rainviewer.com' or not isinstance(payload.get('radar',{}).get('past'),list):
        raise ValueError('Radar timeline unavailable')
    frames=[]
    for frame in payload['radar']['past']:
        path=frame.get('path','')
        if not re.fullmatch(r'/v2/radar/[A-Za-z0-9_-]+',path):continue
        frames.append({'time':frame['time'],'tiles':payload['host']+path+'/256/{z}/{x}/{y}/2/1_1.png'})
    if not frames:raise ValueError('No radar frames')
    return {'frames':frames,'source':'RainViewer','count':len(frames),'observed_at':datetime.fromtimestamp(frames[-1]['time'],timezone.utc).isoformat()}
