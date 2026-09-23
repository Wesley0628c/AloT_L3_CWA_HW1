"""
FastAPI Router for SQLite Temperature Forecasts & SQL Queries (forecasts.py)
"""

from fastapi import APIRouter, HTTPException, Query
from app.database import get_regional_forecasts, execute_raw_sql

router = APIRouter(prefix="/api/forecasts", tags=["Forecasts & SQL"])

@router.get("/regions")
async def get_forecast_regions():
    """
    Module 13: Get Available Forecast Regions
    """
    return {
        "regions": ["北部地區", "中部地區", "南部地區", "東部地區"]
    }

@router.get("/chart")
async def get_forecast_chart_data(region: str = Query(default="ALL")):
    """
    Module 14: Get MinT / MaxT / AvgT Time-Series Data for Line Chart Rendering
    """
    data = get_regional_forecasts(region)
    return {
        "region": region,
        "count": len(data),
        "forecasts": data
    }

@router.get("/table")
async def get_forecast_table_data(region: str = Query(default="ALL")):
    """
    Module 15: Get Tabular Data Records for Table Component
    """
    data = get_regional_forecasts(region)
    return {
        "count": len(data),
        "rows": data
    }

@router.get("/sql-query")
async def run_sql_query(query: str = Query(..., example="SELECT * FROM TemperatureForecasts LIMIT 5")):
    """
    Module 10 & 12: Execute SQL SELECT Statement on SQLite DB
    """
    try:
        results = execute_raw_sql(query)
        return {
            "query": query,
            "status": "success",
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
