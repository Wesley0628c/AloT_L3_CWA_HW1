"""Export only public weather data and the frontend for GitHub Pages."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('BACKGROUND_REFRESH', 'false')
from app import database
from app.config import settings
from app.sources import capabilities, MAP_TILES, enabled_products
from app.services.temperature_service import temperature_service
from app.services.forecast_service import forecast_service, records_csv
from app.services.weather_service import weather_service


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def export_public(output, latest, forecast, products):
    if not latest.get('stations') or not forecast.get('forecasts'):
        raise RuntimeError('Refusing to publish an empty weather site')
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(ROOT / 'frontend', output)
    data = output / 'data'
    data.mkdir()
    history = data / 'history'
    history.mkdir()
    snapshots = database.list_snapshots()
    # Bound public storage; the full local database is never copied to the site.
    if len(snapshots) > 168:
        snapshots = [snapshots[round(i * (len(snapshots)-1)/167)] for i in range(168)]
    for i, row in enumerate(snapshots):
        row['file'] = f'data/history/{i}.json'
        write_json(output / row['file'], database.get_snapshot(row['captured_at']))
    radar = products.get('radar', {})
    if radar.get('available'):
        blob = weather_service.image()
        if blob:
            (data / 'radar.png').write_bytes(blob)
            radar['image_url'] = './data/radar.png'
        else:
            radar['available'] = False
    checked = capabilities()
    manifest = {
        'published_at': datetime.now(timezone.utc).isoformat(),
        'latest': latest, 'forecast': forecast, 'products': products,
        'capabilities': {'supported': {k: v.get('supported', False) for k, v in checked['sources'].items()},
                         'checked_at': checked.get('checked_at'), 'map_tiles': MAP_TILES},
        'history': {'snapshots': snapshots, 'retention_days': 7},
    }
    write_json(data / 'weather.json', manifest)
    fields = ['regionName','dataDate','minT','maxT','avgT']
    for region in ['ALL', *database.REGIONS]:
        rows = [r for r in forecast['forecasts'] if region == 'ALL' or r['regionName'] == region]
        (data / f'forecast-{region}.csv').write_text(records_csv(rows, fields), encoding='utf-8')
    (data / 'stations.csv').write_text(records_csv(latest['stations'], list(latest['stations'][0])), encoding='utf-8')
    # A new database contains only public forecast rows, never settings or caches.
    with sqlite3.connect(data / 'forecasts.sqlite') as db:
        db.execute('CREATE TABLE WeeklyForecasts (regionName TEXT, dataDate TEXT, minT REAL, maxT REAL, avgT REAL)')
        db.executemany('INSERT INTO WeeklyForecasts VALUES (:regionName,:dataDate,:minT,:maxT,:avgT)', forecast['forecasts'])
    html = (output / 'index.html').read_text()
    html = html.replace('<head>', '<head>\n<script>window.CWA_STATIC=true;</script>')
    html = html.replace('<div class="meta">', '<div class="meta"><p>公開版約每 10 分鐘排程更新，可能延遲。</p>')
    html = html.replace('↻ 重新整理', '↻ 讀取已發布資料')
    (output / 'index.html').write_text(html, encoding='utf-8')
    (output / '.nojekyll').touch()
    if settings.CWA_API_KEY:
        key = settings.CWA_API_KEY.encode()
        for file in output.rglob('*'):
            if file.is_file() and key in file.read_bytes():
                raise RuntimeError('Secret found in public output; refusing deployment')
    return manifest


async def main():
    import httpx
    database.init_database()
    names = enabled_products()
    results = await asyncio.gather(temperature_service.get_latest_stations(force_refresh=True),
                                   forecast_service.get('ALL', True),
                                   *(weather_service.get(name) for name in names))
    output = ROOT / 'dist'
    manifest = export_public(output, results[0], results[1], dict(zip(names, results[2:])))
    vendor = output / 'js' / 'vendor'
    vendor.mkdir()
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for file in ['dist/sql-wasm.js', 'dist/sql-wasm.wasm', 'LICENSE']:
            response = await client.get('https://cdn.jsdelivr.net/npm/sql.js@1.13.0/' + file)
            response.raise_for_status()
            (vendor / Path(file).name).write_bytes(response.content)
    print('Published snapshot:', manifest['published_at'], 'stations:', len(results[0]['stations']))


if __name__ == '__main__':
    asyncio.run(main())
