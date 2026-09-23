import asyncio
import csv
import io
import math
from datetime import datetime, timedelta, timezone
from app import database
from app.config import settings
from app.services.cwa_client import cwa_client


def parse_forecasts(raw):
    root = raw.get('cwaopendata', raw.get('cwbopendata', {}))
    dataset = root.get('Dataset', root.get('dataset', {}))
    locations = dataset.get('Locations', {}).get('Location', []) or dataset.get('location', [])
    records = []
    for location in locations:
        name = location.get('LocationName') or location.get('locationName')
        if name not in database.REGIONS:
            continue
        values = {'minT': {}, 'maxT': {}}
        for element in location.get('WeatherElement', location.get('weatherElements', [])):
            label = element.get('ElementName', element.get('elementName'))
            if label in ('最低溫度', 'MinT', 'MinTemperature'):
                field, key, combine = 'minT', 'MinTemperature', min
            elif label in ('最高溫度', 'MaxT', 'MaxTemperature'):
                field, key, combine = 'maxT', 'MaxTemperature', max
            else:
                continue
            for period in element.get('Time', element.get('daily', [])):
                date = (period.get('StartTime') or period.get('dataDate') or '')[:10]
                value = period.get('ElementValue', {}).get(key)
                if value is None:
                    value = period.get('temperature', period.get('ElementValue', {}).get('temperature'))
                try:
                    datetime.strptime(date, '%Y-%m-%d')
                    number = float(value)
                    if not math.isfinite(number) or not -20 <= number <= 50:
                        continue
                except (TypeError, ValueError):
                    continue
                previous = values[field].get(date, number)
                values[field][date] = combine(previous, number)
        for date in sorted(values['minT'].keys() & values['maxT'].keys()):
            low, high = values['minT'][date], values['maxT'][date]
            if low <= high:
                records.append({'regionName': name, 'dataDate': date, 'minT': low, 'maxT': high, 'avgT': round((low+high)/2, 1)})
    return records

class ForecastService:
    def __init__(self):
        self.lock = None
        self.failed = False
        self.last_attempt = None

    async def refresh(self, force=False):
        if self.lock is None:
            self.lock = asyncio.Lock()
        async with self.lock:
            now = datetime.now(timezone.utc)
            updated = database.forecast_updated_at()
            if not force and updated and (now-datetime.fromisoformat(updated)).total_seconds() < settings.CACHE_TTL_SECONDS:
                return
            if not force and self.last_attempt and (now-self.last_attempt).total_seconds() < 60:
                return
            self.last_attempt = now
            payload = await cwa_client.fetch_json(settings.FORECAST_URL)
            try:
                records = parse_forecasts(payload) if payload else []
            except (AttributeError, TypeError, ValueError):
                records = []
            start = database.today()
            end = start + timedelta(days=6)
            records = [r for r in records if start.isoformat() <= r['dataDate'] <= end.isoformat()]
            dates = {r['dataDate'] for r in records}
            complete = dates and all({r['regionName'] for r in records if r['dataDate']==d} == set(database.REGIONS) for d in dates)
            if complete:
                database.save_forecasts(records, now.isoformat())
                self.failed = False
            else:
                self.failed = True

    async def get(self, region=None, force=False):
        await self.refresh(force)
        records = database.get_regional_forecasts(region)
        updated = database.forecast_updated_at()
        stale = self.failed or not updated or (datetime.now(timezone.utc)-datetime.fromisoformat(updated)).total_seconds() > settings.CACHE_TTL_SECONDS
        dates = sorted({r['dataDate'] for r in records})
        return {'region': region or 'ALL', 'count': len(records), 'forecasts': records, 'rows': records,
                'updated_at': updated, 'stale': bool(stale), 'dates': dates, 'partial': len(dates) < 7}

forecast_service = ForecastService()

def records_csv(records, fields):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for record in records:
        safe = dict(record)
        for key, value in safe.items():
            if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
                safe[key] = "'" + value
        writer.writerow(safe)
    return '\ufeff' + output.getvalue()
