"""
CWA API Probe & SQLite Database Test Script (probe_cwa_api.py)
Modules 3 - 10: AI 創新微課程 Taiwan Weather Forecast Realization
"""

import os
import sys
import json
import sqlite3
import ssl
import urllib.request
from datetime import datetime

# Set UTF-8 encoding for Windows stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "data.db")
CWA_API_KEY = "CWA-58A4BB8E-5E3A-41EF-98A9-753DD0F1EF89"
CWA_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001?Authorization={CWA_API_KEY}"

def init_sqlite_db():
    """
    Module 8 & 9: Create SQLite Database (data.db) and Tables
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Module 9: TemperatureForecasts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TemperatureForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT NOT NULL,
            dataDate TEXT NOT NULL,
            minT REAL NOT NULL,
            maxT REAL NOT NULL,
            avgT REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # StationObservations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StationObservations (
            station_id TEXT PRIMARY KEY,
            station_name TEXT NOT NULL,
            county TEXT,
            town TEXT,
            lat REAL,
            lon REAL,
            temperature_c REAL,
            humidity_percent REAL,
            wind_speed_mps REAL,
            precipitation_mm REAL,
            observed_at TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"[SQLite] Database initialized at: {DB_PATH}")

def probe_cwa_api():
    """
    Module 3, 4, 5, 6, 7: Probe CWA OpenData API and parse JSON data
    """
    print(f"[Probe] Requesting CWA OpenData API: {CWA_URL[:50]}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(CWA_URL, headers={"User-Agent": "CWA-Probe-Client/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
        payload = json.loads(response.read().decode('utf-8'))

    records = payload.get("records", {}).get("Station", [])
    print(f"[Probe] Successfully fetched {len(records)} raw weather station records from CWA API!")

    stations = []
    region_temps = {"北部地區": [], "中部地區": [], "南部地區": [], "東部地區": []}

    for raw in records:
        try:
            st_id = raw.get("StationId")
            st_name = raw.get("StationName")
            geo = raw.get("GeoInfo", {})
            county = geo.get("CountyName", "")
            town = geo.get("TownName", "")
            lat = float(geo.get("Coordinates", [{}])[0].get("StationLatitude", 0) or 0)
            lon = float(geo.get("Coordinates", [{}])[0].get("StationLongitude", 0) or 0)

            obs = raw.get("WeatherElement", {})
            temp = float(obs.get("AirTemperature", -99))
            hum = float(obs.get("RelativeHumidity", -99))
            wind = float(obs.get("WindSpeed", -99))
            precip = float(obs.get("Now", {}).get("Precipitation", 0) or 0)
            obs_time = raw.get("ObsTime", {}).get("DateTime", "")

            if -20.0 <= temp <= 50.0:
                stations.append((st_id, st_name, county, town, lat, lon, temp, hum, wind, precip, obs_time))

                # Group by Region (Module 6 & 7)
                if county in ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"]:
                    region_temps["北部地區"].append(temp)
                elif county in ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"]:
                    region_temps["中部地區"].append(temp)
                elif county in ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣", "澎湖縣"]:
                    region_temps["南部地區"].append(temp)
                elif county in ["花蓮縣", "臺東縣", "金門縣", "連江縣"]:
                    region_temps["東部地區"].append(temp)
        except Exception as e:
            continue

    return stations, region_temps

def save_to_sqlite(stations, region_temps):
    """
    Module 8: Insert cleaned data into SQLite database
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Save Station Observations
    cursor.executemany("""
        INSERT OR REPLACE INTO StationObservations 
        (station_id, station_name, county, town, lat, lon, temperature_c, humidity_percent, wind_speed_mps, precipitation_mm, observed_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, stations)

    # Save Regional Forecast Summary
    today_str = datetime.now().strftime("%Y-%m-%d")
    for region, temps in region_temps.items():
        if temps:
            min_t = round(min(temps), 1)
            max_t = round(max(temps), 1)
            avg_t = round(sum(temps) / len(temps), 1)
            cursor.execute("""
                INSERT INTO TemperatureForecasts (regionName, dataDate, minT, maxT, avgT)
                VALUES (?, ?, ?, ?, ?)
            """, (region, today_str, min_t, max_t, avg_t))

    conn.commit()
    conn.close()
    print(f"[SQLite] Saved {len(stations)} station records and 4 regional forecasts into SQLite database!")

def verify_sql_queries():
    """
    Module 10 & 12: Query SQLite Database using SQL statements
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n[SQL Verification] Query 1: SELECT DISTINCT regionName FROM TemperatureForecasts")
    cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts")
    regions = cursor.fetchall()
    print("   Result Regions:", [r[0] for r in regions])

    print("\n[SQL Verification] Query 2: SELECT regionName, dataDate, minT, maxT, avgT FROM TemperatureForecasts ORDER BY id DESC LIMIT 4")
    cursor.execute("SELECT regionName, dataDate, minT, maxT, avgT FROM TemperatureForecasts ORDER BY id DESC LIMIT 4")
    rows = cursor.fetchall()

    print("+--------------+------------+--------+--------+--------+")
    print("| regionName   | dataDate   | minT C | maxT C | avgT C |")
    print("+--------------+------------+--------+--------+--------+")
    for r in rows:
        print(f"| {r[0]:<12} | {r[1]:<10} | {r[2]:<6} | {r[3]:<6} | {r[4]:<6} |")
    print("+--------------+------------+--------+--------+--------+")

    conn.close()

if __name__ == "__main__":
    print("[Module 1-12] Starting CWA API Probe & SQLite Database Pipeline Test...\n")
    init_sqlite_db()
    stations, region_temps = probe_cwa_api()
    save_to_sqlite(stations, region_temps)
    verify_sql_queries()
    print("\n[Complete] CWA Probe & SQLite Verification Finished Successfully!")
