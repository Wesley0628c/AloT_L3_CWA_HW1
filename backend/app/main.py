import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings, ROOT
from app.database import init_database
from app.routers import health, temperature, forecasts
from app.services.temperature_service import temperature_service
from app.services.forecast_service import forecast_service

async def refresh_loop():
    while True:
        results = await asyncio.gather(temperature_service.get_latest_stations(force_refresh=True),
                                       forecast_service.refresh(force=True), return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logging.getLogger(__name__).warning('Background refresh failed (%s)', type(result).__name__)
        await asyncio.sleep(settings.CACHE_TTL_SECONDS)

@asynccontextmanager
async def lifespan(app):
    init_database()
    task = asyncio.create_task(refresh_loop()) if settings.BACKGROUND_REFRESH else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

app = FastAPI(title='台灣氣象整合平台', version='2.0.0', lifespan=lifespan)
app.include_router(health.router)
app.include_router(temperature.router)
app.include_router(forecasts.router)

@app.get('/api/config')
def frontend_config():
    # Windy Map Forecast keys are intentionally browser-visible. Never expose the CWA key.
    return {'windy_api_key': settings.WINDY_API_KEY}

app.mount('/', StaticFiles(directory=str(ROOT / 'frontend'), html=True), name='static')
