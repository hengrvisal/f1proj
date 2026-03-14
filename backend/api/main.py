"""Minimal FastAPI health check stub."""

from fastapi import FastAPI
from sqlalchemy import text

from backend.database import engine

app = FastAPI(title="F1 AI Platform", version="0.1.0")


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}
