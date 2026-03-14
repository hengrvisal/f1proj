"""Tests for telemetry resampling logic."""

import numpy as np
import pandas as pd

from backend.ingestion.ingest_telemetry import resample_telemetry


def test_resample_basic():
    # Create fake telemetry with 1m resolution over 100m
    tel = pd.DataFrame({
        "Distance": np.arange(0, 100, 1).astype(float),
        "Speed": np.linspace(100, 300, 100),
        "Throttle": np.full(100, 80.0),
        "nGear": np.full(100, 5),
        "Brake": np.zeros(100, dtype=bool),
        "DRS": np.full(100, 0),
        "RPM": np.full(100, 10000.0),
        "X": np.linspace(0, 500, 100),
        "Y": np.linspace(0, 200, 100),
    })

    result = resample_telemetry(tel, lap_distance=100)
    # Should have points at 0, 10, 20, ..., 100 = 11 points
    assert len(result) == 11
    assert list(result["distance_m"]) == list(range(0, 110, 10))
    # Speed should interpolate correctly
    assert result["speed"].iloc[0] < result["speed"].iloc[-1]


def test_resample_empty():
    result = resample_telemetry(pd.DataFrame())
    assert result.empty
