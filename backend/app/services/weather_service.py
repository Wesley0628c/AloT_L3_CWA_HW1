"""Independent product caches so one unavailable API never blanks all weather layers."""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
import httpx
from app import database
from app.config import settings
from app.sources import SOURCES
from app.services.cwa_client import cwa_client
from app.services.products import parse_rainfall, parse_warnings, parse_typhoons, parse_radar, parse_radar_frames
from app.services.wind_service import fetch_wind

PARSERS={'rainfall':parse_rainfall,'warnings':parse_warnings,'typhoon':parse_typhoons,'radar':parse_radar,'rainviewer':parse_radar_frames}

class WeatherService:
    def __init__(self):
        self.cache={};self.locks={};self.attempts={};self.failed=set()
        self.radar_image=None

    async def fetch(self,name):
        if name=='gfs_wind':return await fetch_wind()
        source=SOURCES[name]
        if source.get('auth'):
            payload=await cwa_client.fetch_json(source['url'])
            if payload is None:raise ValueError('CWA unavailable')
        else:
            async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
                response=await client.get(source['url']);response.raise_for_status();payload=response.json()
        data=PARSERS[name](payload)
        if name=='radar':
            async with httpx.AsyncClient(timeout=20) as client:
                response=await client.get(data['image_source']);response.raise_for_status()
                if not response.content.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Radar image invalid')
                self.radar_image=response.content
                folder=Path(database.DB_PATH).parent/'cache';folder.mkdir(parents=True,exist_ok=True)
                temp=folder/'radar.tmp';temp.write_bytes(response.content);temp.replace(folder/'radar.png')
        return data

    async def get(self,name,force=False):
        if name not in PARSERS and name!='gfs_wind':raise ValueError('Unknown weather product')
        if name not in self.locks:self.locks[name]=asyncio.Lock()
        async with self.locks[name]:
            now=datetime.now(timezone.utc)
            if name not in self.cache:
                saved=database.get_product(name)
                if saved:self.cache[name]=saved
            cached=self.cache.get(name)
            ttl=3600 if name=='gfs_wind' else settings.CACHE_TTL_SECONDS
            expired=not cached or (now-datetime.fromisoformat(cached['updated_at'])).total_seconds()>=ttl
            retry=not self.attempts.get(name) or (now-self.attempts[name]).total_seconds()>=60
            if force or (expired and retry):
                self.attempts[name]=now
                try:
                    body=await self.fetch(name)
                    cached={'body':body,'updated_at':now.isoformat()}
                    database.save_product(name,body,cached['updated_at'])
                    self.cache[name]=cached;self.failed.discard(name)
                except Exception as exc:
                    self.failed.add(name)
                    logging.getLogger(__name__).warning('%s refresh failed (%s)',name,type(exc).__name__)
            if not cached:return {'available':False,'stale':True,'updated_at':None}
            body=dict(cached['body'])
            if name=='warnings':
                body['warnings']=[w for w in body['warnings'] if datetime.fromisoformat(w['ends_at'])>now]
                for w in body['warnings']:w['active']=not w['starts_at'] or datetime.fromisoformat(w['starts_at'])<=now
                body['count']=len(body['warnings'])
            if name=='typhoon':
                body['typhoons']=[s for s in body['typhoons'] if (now-datetime.fromisoformat(s['current']['time'])).total_seconds()<86400]
                body['count']=len(body['typhoons'])
            stale=name in self.failed or (now-datetime.fromisoformat(cached['updated_at'])).total_seconds()>=ttl
            timestamp=body.get('observed_at') or body.get('valid_at')
            if timestamp:
                max_age=21600 if name=='gfs_wind' else 3600
                stale=stale or (now-datetime.fromisoformat(timestamp)).total_seconds()>max_age
            return {**body,'available':True,'stale':stale,'updated_at':cached['updated_at']}

    def image(self):
        if self.radar_image is not None:return self.radar_image
        file=Path(database.DB_PATH).parent/'cache'/'radar.png'
        return file.read_bytes() if file.exists() else None

weather_service=WeatherService()
