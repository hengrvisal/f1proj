"""F1 AI Platform API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.api.routers import ai_analysis, circuits, driver_dna, drivers, races, season_metrics, telemetry, tyre_deg
from backend.database import engine

app = FastAPI(title="F1 AI Platform", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drivers.router)
app.include_router(driver_dna.router)
app.include_router(ai_analysis.router)
app.include_router(telemetry.router)
app.include_router(tyre_deg.router)
app.include_router(circuits.router)
app.include_router(races.router)
app.include_router(season_metrics.router)


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}
