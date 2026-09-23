import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import temperature, health

app = FastAPI(
    title="CWA Temperature Broadcast API",
    description="Backend API for fetching, cleaning, and serving CWA station temperature observations on Windy Map.",
    version="1.0.0"
)

# Enable CORS for local development & frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(temperature.router)
app.include_router(health.router)

# Mount Frontend static files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
