"""
SQLite Database Access Layer (database.py)
"""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.db")

def get_db_connection():
    """
    Get SQLite Database Connection
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """
    Initialize SQLite Tables
    """
    conn = get_db_connection()
    cursor = conn.cursor()

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

def get_regional_forecasts(region_name: str = None):
    """
    Fetch Regional Forecast Time-Series from SQLite DB
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if region_name and region_name != "ALL":
        cursor.execute("""
            SELECT id, regionName, dataDate, minT, maxT, avgT, created_at
            FROM TemperatureForecasts
            WHERE regionName = ?
            ORDER BY id ASC LIMIT 30
        """, (region_name,))
    else:
        cursor.execute("""
            SELECT id, regionName, dataDate, minT, maxT, avgT, created_at
            FROM TemperatureForecasts
            ORDER BY id DESC LIMIT 50
        """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def execute_raw_sql(sql_query: str):
    """
    Execute Safe Read-Only SELECT SQL Query
    """
    if not sql_query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for security.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
