"""Verified upstream endpoints shared by the application and the probe command."""
CWA_REST = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/'
CWA_FILE = 'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/'
SOURCES = {
    'automatic': {'url': CWA_REST+'O-A0001-001', 'auth': True, 'format': 'stations'},
    'bureau': {'url': CWA_REST+'O-A0003-001', 'auth': True, 'format': 'stations'},
    'rainfall': {'url': CWA_REST+'O-A0002-001', 'auth': True, 'format': 'rainfall'},
    'forecast': {'url': CWA_FILE+'F-C0032-003', 'auth': True, 'format': 'forecast'},
    'typhoon': {'url': CWA_REST+'W-C0034-005', 'auth': True, 'format': 'typhoon'},
    'warnings': {'url': CWA_REST+'W-C0033-002', 'auth': True, 'format': 'warnings'},
    'radar': {'url': CWA_FILE+'O-A0058-006', 'auth': True, 'format': 'radar'},
    'dark_map': {'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/8/110/213', 'format': 'image'},
    'street_map': {'url': 'https://tile.openstreetmap.org/8/213/110.png', 'format': 'image'},
    'boundaries': {'url': 'https://wmts.nlsc.gov.tw/wmts/CITY/default/EPSG:3857/8/110/213', 'format': 'image'},
    'rainviewer': {'url': 'https://api.rainviewer.com/public/weather-maps.json', 'format': 'radar_frames'},
    'gfs_wind': {'url': 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl', 'format': 'grib'},
}
RADAR_IMAGE_HOST = 'cwaopendata.s3.ap-northeast-1.amazonaws.com'
MAP_TILES = {
    'dark': 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    'street': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    'boundaries': 'https://wmts.nlsc.gov.tw/wmts/CITY/default/EPSG:3857/{z}/{y}/{x}',
}


def capabilities():
    import json
    from pathlib import Path
    file=Path(__file__).resolve().parents[2]/'config'/'api_capabilities.json'
    return json.loads(file.read_text()) if file.exists() else {'sources':{}}


def enabled_products():
    checked=capabilities()['sources']
    return [name for name in ('rainfall','warnings','typhoon','radar','rainviewer','gfs_wind')
            if checked.get(name,{}).get('supported')]
