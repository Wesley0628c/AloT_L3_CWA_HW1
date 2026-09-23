import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.config import settings

DB_PATH = settings.DATABASE_PATH
TAIPEI = timezone(timedelta(hours=8))
REGIONS = ['北部地區', '中部地區', '南部地區', '東北部地區', '東部地區', '東南部地區']

def today():
    return datetime.now(TAIPEI).date()

@contextmanager
def connection(readonly=False):
    path = Path(DB_PATH).resolve()
    if readonly:
        conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=10)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        if not readonly:
            conn.commit()
    finally:
        conn.close()

def init_database():
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS WeeklyForecasts (
            regionName TEXT NOT NULL, dataDate TEXT NOT NULL,
            minT REAL NOT NULL, maxT REAL NOT NULL, avgT REAL NOT NULL,
            PRIMARY KEY(regionName, dataDate), CHECK(minT <= maxT)
        );
        CREATE TABLE IF NOT EXISTS ProductCache (name TEXT PRIMARY KEY, body TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS UpdateMetadata (name TEXT PRIMARY KEY, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ObservationSnapshots (
            captured_at TEXT PRIMARY KEY, stations TEXT NOT NULL, count INTEGER NOT NULL,
            partial INTEGER NOT NULL DEFAULT 0
        );
        """)
        if 'partial' not in {r['name'] for r in conn.execute('PRAGMA table_info(ObservationSnapshots)')}:
            conn.execute('ALTER TABLE ObservationSnapshots ADD COLUMN partial INTEGER NOT NULL DEFAULT 0')

def save_forecasts(records, updated_at):
    with connection() as conn:
        # Replace atomically: obsolete days must not leak into the next forecast window.
        conn.execute('DELETE FROM WeeklyForecasts')
        conn.executemany('INSERT INTO WeeklyForecasts VALUES (:regionName,:dataDate,:minT,:maxT,:avgT)', records)
        conn.execute('INSERT OR REPLACE INTO UpdateMetadata VALUES (?,?)', ('forecast', updated_at))

def forecast_updated_at():
    with connection(True) as conn:
        row = conn.execute("SELECT updated_at FROM UpdateMetadata WHERE name='forecast'").fetchone()
    return row[0] if row else None

def get_regional_forecasts(region_name=None):
    start = today()
    end = start + timedelta(days=6)
    query = 'SELECT * FROM WeeklyForecasts WHERE dataDate BETWEEN ? AND ?'
    args = [start.isoformat(), end.isoformat()]
    if region_name and region_name != 'ALL':
        query += ' AND regionName=?'; args.append(region_name)
    query += ' ORDER BY dataDate, regionName'
    with connection(True) as conn:
        return [dict(row) for row in conn.execute(query, args)]

def save_snapshot(stations, captured_at, partial=False):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with connection() as conn:
        conn.execute('INSERT OR REPLACE INTO ObservationSnapshots (captured_at,stations,count,partial) VALUES (?,?,?,?)',
                     (captured_at, json.dumps(stations, ensure_ascii=False), len(stations), int(partial)))
        conn.execute('DELETE FROM ObservationSnapshots WHERE captured_at < ?', (cutoff,))

def list_snapshots():
    with connection(True) as conn:
        return [dict(r) for r in conn.execute('SELECT captured_at, count FROM ObservationSnapshots ORDER BY captured_at DESC LIMIT 1008')]

def get_snapshot(captured_at=None):
    with connection(True) as conn:
        if captured_at:
            row = conn.execute('SELECT * FROM ObservationSnapshots WHERE captured_at=?', (captured_at,)).fetchone()
        else:
            row = conn.execute('SELECT * FROM ObservationSnapshots ORDER BY captured_at DESC LIMIT 1').fetchone()
    if not row:
        return None
    return {'updated_at': row['captured_at'], 'count': row['count'], 'stations': json.loads(row['stations']), 'partial': bool(row['partial'])}

def execute_raw_sql(sql_query):
    if not sql_query.strip().upper().startswith('SELECT'):
        raise ValueError('僅允許 SELECT 查詢')
    with connection(True) as conn:
        conn.execute('PRAGMA query_only=ON')
        # Bound expensive recursive queries as well as returned data.
        calls = [0]
        def budget():
            calls[0] += 1
            return int(calls[0] > 1000)
        conn.set_progress_handler(budget, 1000)
        return [dict(r) for r in conn.execute(sql_query).fetchmany(500)]


def save_product(name, body, updated_at):
    with connection() as conn:
        conn.execute('INSERT OR REPLACE INTO ProductCache VALUES (?,?,?)',
                     (name, json.dumps(body, ensure_ascii=False, allow_nan=False), updated_at))


def get_product(name):
    with connection(True) as conn:
        row=conn.execute('SELECT body,updated_at FROM ProductCache WHERE name=?',(name,)).fetchone()
    return {'body':json.loads(row['body']),'updated_at':row['updated_at']} if row else None
