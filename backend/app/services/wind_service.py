"""Small NOAA GFS 10 m wind subset, decoded with ECMWF ecCodes."""
import asyncio
import math
import tempfile
from datetime import datetime, timedelta, timezone
import httpx
from app.sources import SOURCES


def wind_requests(now=None):
    now=now or datetime.now(timezone.utc)
    available=now-timedelta(hours=5)
    latest=available.replace(hour=(available.hour//6)*6,minute=0,second=0,microsecond=0)
    for back in range(2):
        run=latest-timedelta(hours=6*back)
        hour=max(0,int((now-run).total_seconds()//10800)*3)
        yield {'dir':f'/gfs.{run:%Y%m%d}/{run:%H}/atmos','file':f'gfs.t{run:%H}z.pgrb2.0p25.f{hour:03d}',
               'lev_10_m_above_ground':'on','var_UGRD':'on','var_VGRD':'on','subregion':'',
               'leftlon':'110','rightlon':'145','toplat':'34','bottomlat':'12'}


def decode_wind(blob):
    if not blob.startswith(b'GRIB'):raise ValueError('Not a GRIB product')
    import eccodes as ec
    components={};geometry=None;valid=None;run=None
    with tempfile.TemporaryFile() as file:
        file.write(blob);file.seek(0)
        while True:
            handle=ec.codes_grib_new_from_file(file)
            if handle is None:break
            try:
                name=ec.codes_get(handle,'shortName')
                key='u' if name in ('10u','u10') else 'v' if name in ('10v','v10') else None
                if not key:continue
                lat=ec.codes_get_array(handle,'latitudes');lon=ec.codes_get_array(handle,'longitudes');values=ec.codes_get_values(handle)
                lats=sorted({round(float(v),6) for v in lat},reverse=True)
                lons=sorted({round(float(v),6) for v in lon})
                current=(lats,lons)
                if geometry is not None and geometry!=current:raise ValueError('Wind grids do not align')
                geometry=current
                lookup={(round(float(a),6),round(float(b),6)):float(v) for a,b,v in zip(lat,lon,values)}
                components[key]=[round(lookup[(a,b)],3) if math.isfinite(lookup[(a,b)]) and abs(lookup[(a,b)])<200 else None for a in lats for b in lons]
                stamp=f"{ec.codes_get(handle,'validityDate')}{ec.codes_get(handle,'validityTime'):04d}"
                valid=datetime.strptime(stamp,'%Y%m%d%H%M').replace(tzinfo=timezone.utc).isoformat()
                run=f"{ec.codes_get(handle,'dataDate')} {ec.codes_get(handle,'dataTime'):04d} UTC"
            finally:ec.codes_release(handle)
    if set(components)!= {'u','v'} or not geometry:raise ValueError('Missing 10 m U/V components')
    lats,lons=geometry
    return {'source':'NOAA GFS 0.25°・10 m 風場模型','run':run,'valid_at':valid,
            'width':len(lons),'height':len(lats),'west':lons[0],'east':lons[-1],'north':lats[0],'south':lats[-1],
            'dx':lons[1]-lons[0],'dy':lats[0]-lats[1],**components}


async def fetch_wind():
    async with httpx.AsyncClient(timeout=30,follow_redirects=True) as client:
        for params in wind_requests():
            try:
                response=await client.get(SOURCES['gfs_wind']['url'],params=params)
                response.raise_for_status()
                return await asyncio.to_thread(decode_wind,response.content)
            except (httpx.HTTPError,ValueError):continue
    raise ValueError('GFS currently unavailable')
