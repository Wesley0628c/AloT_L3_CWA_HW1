"""
FastAPI Main Application (app/main.py)
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import health, temperature, forecasts
from app.database import init_database

app = FastAPI(
    title="Taiwan CWA Weather Broadcast API",
    description="FastAPI Backend for CWA Weather Observations, SQLite Storage, and Windy Map Visualizations",
    version="1.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLite Database on startup
@app.on_event("startup")
def on_startup():
    init_database()

# Include Routers
app.include_router(health.router)
app.include_router(temperature.router)
app.include_router(forecasts.router)

# Mount Frontend Static Directory
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
