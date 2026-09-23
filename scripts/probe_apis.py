#!/usr/bin/env python3
"""Probe HTTP, payload schemas, image bytes and GRIB U/V decoding before enabling layers."""
import asyncio
import json
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import httpx
from app.config import settings
from app.sources import SOURCES
from app.services.weather_service import PARSERS
from app.services.forecast_service import parse_forecasts
from app.services.temperature_service import TemperatureService
from app.services.wind_service import fetch_wind


def image_valid(blob):
    return blob.startswith(b'\x89PNG\r\n\x1a\n') or blob.startswith(b'\xff\xd8\xff')


async def probe(name,source,client):
    started=time.monotonic()
    result={'endpoint':source['url'],'supported':False}
    try:
        if source.get('auth') and not settings.CWA_API_KEY:
            result['reason']='CWA_API_KEY is not configured';return result
        if name=='gfs_wind':
            data=await fetch_wind()
            result.update(supported=True,status=200,format='GRIB2 decoded: 10 m U/V',width=data['width'],height=data['height'],valid_at=data['valid_at'])
            return result
        response=await client.get(source['url'],params={'Authorization':settings.CWA_API_KEY,'format':'JSON'} if source.get('auth') else None)
        result.update(status=response.status_code,content_type=response.headers.get('content-type'),bytes=len(response.content))
        response.raise_for_status()
        if source['format']=='image':
            if not image_valid(response.content):raise ValueError('Response is not an image')
            result['supported']=True
        else:
            payload=response.json()
            if name in ('automatic','bureau'):
                data=payload.get('records',{}).get('Station')
                if not isinstance(data,list):raise ValueError('Station schema missing')
                parsed=[s for s in (TemperatureService()._parse_station(row) for row in data) if s]
                if not parsed:raise ValueError('No valid observations')
                result['count']=len(parsed)
                result['fields']={field:sum(s.get(field) is not None for s in parsed) for field in ['temperature_c','humidity_percent','wind_speed_mps','wind_direction_deg','weather']}
            elif name=='forecast':
                parsed=parse_forecasts(payload)
                if len({r['regionName'] for r in parsed})!=6:raise ValueError('Six regions unavailable')
                result['count']=len(parsed)
            else:
                parsed=PARSERS[name](payload)
                result['count']=parsed.get('count')
                if name=='radar':
                    image=await client.get(parsed['image_source']);image.raise_for_status()
                    if not image_valid(image.content):raise ValueError('Radar image invalid')
                    result.update(image_status=image.status_code,image_dimensions=list(struct.unpack('>II',image.content[16:24])),bounds=parsed['bounds'])
                if name=='rainviewer':
                    tile_url=parsed['frames'][-1]['tiles'].format(z=8,x=213,y=110)
                    tile=await client.get(tile_url);tile.raise_for_status()
                    if not image_valid(tile.content):raise ValueError('Radar tile invalid')
                    result['tile_status']=tile.status_code
            result['supported']=True
    except Exception as exc:
        result['reason']=type(exc).__name__
    finally:
        result['elapsed_ms']=round((time.monotonic()-started)*1000)
    return result


async def main():
    async with httpx.AsyncClient(timeout=30,follow_redirects=True) as client:
        entries=await asyncio.gather(*(probe(name,source,client) for name,source in SOURCES.items()))
    results=dict(zip(SOURCES,entries))
    results['windy']={'supported':False,'reason':'Removed: no verified Windy Map Forecast credential; NOAA GFS supplies the supported wind model.'}
    report={'project':'AloT_L3_CWA_HW1','checked_at':datetime.now(timezone.utc).isoformat(),'sources':results}
    output=ROOT/'config'/'api_capabilities.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# API probe 實測結果','',f"檢查時間：{report['checked_at']}",'',
           '執行：`python scripts/probe_apis.py`。除了 HTTP 狀態，也檢查資料結構、影像位元組與 GRIB 風場解碼；無活動颱風／警報不等於 API 不支援。','',
           '| 來源 | 保留 | HTTP | 驗證內容 |','|---|---|---|---|']
    for name,r in results.items():
        detail=r.get('reason') or (f"{r['count']} 筆／影格" if r.get('count') is not None else r.get('format','影像與格式有效'))
        lines.append(f"| {name} | {'是' if r['supported'] else '否'} | {r.get('status','—')} | {detail} |")
        print(name, 'SUPPORTED' if r['supported'] else 'REMOVED',r.get('status',''),detail)
    lines+=['','探測結果反映檢查當下，不能保證上游永遠可用。執行期也會檢查資料是否可用並標示過期狀態。','',
            '來源定義：`backend/app/sources.py`。金鑰只從 `.env` 讀取，不會寫入報告。']
    path=ROOT/'docs'/'reports'/'api-probe.md';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(lines)+'\n')

if __name__=='__main__':asyncio.run(main())
