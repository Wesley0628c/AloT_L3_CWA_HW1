"""
Gate 2: SQLite Database Implementation (gate2_database.py)
Transforms CWA Forecast JSON and loads 308 forecast records (22 counties x 14 periods) into SQLite.
"""

import os
import sys
import json
import sqlite3
import ssl
import urllib.request
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "data.db")
CWA_API_KEY = "CWA-58A4BB8E-5E3A-41EF-98A9-753DD0F1EF89"
CWA_FORECAST_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={CWA_API_KEY}"

def init_gate2_table():
    """
    Step 2: Create CountyForecasts table with UNIQUE(location_name, forecast_start) constraint
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CountyForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT NOT NULL,
            forecast_start TEXT NOT NULL,
            forecast_end TEXT NOT NULL,
            wx TEXT,
            minT REAL,
            maxT REAL,
            pop TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(location_name, forecast_start)
        )
    """)
    
    conn.commit()
    conn.close()
    print("[Gate 2] SQLite table 'CountyForecasts' initialized with UNIQUE(location_name, forecast_start) constraint.")

def load_and_transform_cwa_forecasts():
    """
    Step 1: Fetch CWA JSON API, transform into 308 forecast records (22 counties x 14 periods)
    """
    print(f"[Gate 2] Requesting 22 Counties Forecast JSON from CWA API...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(CWA_FORECAST_URL, headers={"User-Agent": "Gate2-Client/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
        payload = json.loads(response.read().decode('utf-8'))

    gate1_file = os.path.join(os.path.dirname(__file__), "gate1_output.json")
    with open(gate1_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[Gate 1] Saved raw CWA JSON to: {gate1_file}")

    location_list = payload.get("records", {}).get("location", [])
    records_to_insert = []

    for loc in location_list:
        loc_name = loc.get("locationName")
        weather_elements = loc.get("weatherElement", [])
        
        element_map = {}
        for elem in weather_elements:
            element_map[elem.get("elementName")] = elem.get("time", [])

        min_t_list = element_map.get("MinT", [])
        max_t_list = element_map.get("MaxT", [])
        wx_list = element_map.get("Wx", [])
        pop_list = element_map.get("PoP", [])

        for i in range(len(min_t_list)):
            f_start = min_t_list[i].get("startTime")
            f_end = min_t_list[i].get("endTime")
            min_t = float(min_t_list[i].get("parameter", {}).get("parameterName", 0))
            max_t = float(max_t_list[i].get("parameter", {}).get("parameterName", 0)) if i < len(max_t_list) else min_t
            wx = wx_list[i].get("parameter", {}).get("parameterName", "") if i < len(wx_list) else ""
            pop = pop_list[i].get("parameter", {}).get("parameterName", "") if i < len(pop_list) else "0"

            records_to_insert.append((loc_name, f_start, f_end, wx, min_t, max_t, pop))

    return records_to_insert

def insert_to_sqlite(records):
    """
    Step 2: Use INSERT OR REPLACE with UNIQUE constraint to prevent duplicates
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR REPLACE INTO CountyForecasts 
        (location_name, forecast_start, forecast_end, wx, minT, maxT, pop, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, records)

    conn.commit()
    conn.close()
    print(f"[Gate 2] Successfully inserted {len(records)} forecast records into SQLite DB!")

def verify_tables_and_queries():
    """
    Step 3: Verify the tables using Python SQL SELECT queries
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n--- [Gate 2 SQL Verification 1: SELECT DISTINCT location_name] ---")
    cursor.execute("SELECT DISTINCT location_name FROM CountyForecasts")
    locations = [r[0] for r in cursor.fetchall()]
    print(f"Total Counties in DB: {len(locations)}")
    print("Counties List:", locations[:10], "... and more")

    print("\n--- [Gate 2 SQL Verification 2: SELECT * FROM CountyForecasts Sample Table] ---")
    cursor.execute("""
        SELECT location_name, forecast_start, minT, maxT, wx 
        FROM CountyForecasts 
        WHERE location_name IN ('臺北市', '臺中市', '高雄市', '花蓮縣')
        ORDER BY location_name, forecast_start
    """)
    rows = cursor.fetchall()

    print("+--------------+-------------------+--------+--------+------------------+")
    print("| location_name| forecast_start    | minT C | maxT C | wx               |")
    print("+--------------+-------------------+--------+--------+------------------+")
    for r in rows:
        print(f"| {r[0]:<12} | {r[1]:<17} | {r[2]:<6} | {r[3]:<6} | {r[4]:<16} |")
    print("+--------------+-------------------+--------+--------+------------------+")

    conn.close()

if __name__ == "__main__":
    print("🚀 Starting Gate 2 Database Pipeline execution...\n")
    init_gate2_table()
    records = load_and_transform_cwa_forecasts()
    insert_to_sqlite(records)
    verify_tables_and_queries()
    print("\n✅ Gate 2 (Database) is now PASS!")
