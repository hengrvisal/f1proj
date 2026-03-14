"""AI-powered driver analysis using Claude."""

import json

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.config import settings

router = APIRouter(prefix="/api/ai", tags=["ai-analysis"])


def _clamp(value: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(value))))


@router.post("/analyse-driver")
def analyse_driver(
    driver_id: int = Query(...),
    season: int = Query(...),
    db: Session = Depends(get_db),
):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # --- Gather driver info ---
    driver_row = db.execute(text("""
        SELECT DISTINCT ON (d.id)
               d.first_name || ' ' || d.last_name as name,
               c.name as team,
               d.permanent_number
        FROM drivers d
        JOIN driver_race_entries dre ON dre.driver_id = d.id
        JOIN races r ON dre.race_id = r.id
        JOIN seasons s ON r.season_id = s.id
        JOIN constructors c ON dre.constructor_id = c.id
        WHERE d.id = :did AND s.year = :year
        ORDER BY d.id, r.round_number DESC
    """), {"did": driver_id, "year": season}).fetchone()

    if not driver_row:
        raise HTTPException(status_code=404, detail="Driver not found for this season")

    driver_name, team, permanent_number = driver_row

    # --- DNA features ---
    dna_row = db.execute(text("""
        SELECT dna.feature_vector
        FROM driver_dna_features dna
        JOIN seasons s ON dna.season_id = s.id
        WHERE dna.driver_id = :did AND s.year = :year
    """), {"did": driver_id, "year": season}).fetchone()

    if not dna_row or not dna_row[0]:
        raise HTTPException(status_code=404, detail="No DNA features for this driver/season")

    features = json.loads(dna_row[0])
    features.pop("_pca_info", None)

    # Map DNA features to prompt fields
    throttle = _clamp((features.get("corner_exit_efficiency", 0) / 1.6) * 100)
    brake = _clamp(features.get("brake_aggression", 0))
    consistency = _clamp(features.get("consistency", 0) * 100)
    pace = _clamp(features.get("quali_vs_race", 0) * 100)

    # Overtake aggression: scale based on typical range
    raw_agg = features.get("overtake_aggression", 0)
    aggression = _clamp(raw_agg * 100) if raw_agg <= 1.0 else _clamp(raw_agg)

    tyre = _clamp(features.get("tyre_management", 0) * 100)

    # --- Best lap time ---
    best_lap = db.execute(text("""
        SELECT MIN(l.lap_time_ms)
        FROM laps l
        JOIN sessions ses ON l.session_id = ses.id
        JOIN races r ON ses.race_id = r.id
        JOIN seasons s ON r.season_id = s.id
        WHERE l.driver_id = :did AND s.year = :year
          AND ses.session_type = 'Race'
          AND l.lap_time_ms IS NOT NULL
    """), {"did": driver_id, "year": season}).scalar()

    best_lap_str = ""
    if best_lap:
        mins = best_lap // 60000
        secs = (best_lap % 60000) / 1000
        best_lap_str = f"\nBest race lap: {mins}:{secs:06.3f}"

    # --- Sector averages ---
    sector_row = db.execute(text("""
        SELECT AVG(l.sector1_ms), AVG(l.sector2_ms), AVG(l.sector3_ms)
        FROM laps l
        JOIN sessions ses ON l.session_id = ses.id
        JOIN races r ON ses.race_id = r.id
        JOIN seasons s ON r.season_id = s.id
        WHERE l.driver_id = :did AND s.year = :year
          AND ses.session_type = 'Race'
          AND l.is_pit_in_lap IS NOT TRUE
          AND l.is_pit_out_lap IS NOT TRUE
          AND l.sector1_ms IS NOT NULL
          AND l.sector2_ms IS NOT NULL
          AND l.sector3_ms IS NOT NULL
    """), {"did": driver_id, "year": season}).fetchone()

    sector_str = ""
    if sector_row and sector_row[0]:
        s1 = sector_row[0] / 1000
        s2 = sector_row[1] / 1000
        s3 = sector_row[2] / 1000
        sector_str = f"\nSector 1 avg: {s1:.3f}s\nSector 2 avg: {s2:.3f}s\nSector 3 avg: {s3:.3f}s"

    # --- Build prompt ---
    prompt = f"""You are an elite Formula 1 analyst. Analyse the following driver based on their telemetry-derived stats.

Driver: {driver_name}
Team: {team}
Number: {permanent_number or 'N/A'}
Season: {season}

Performance Metrics (0-100 scale):
- Throttle application: {throttle}
- Brake aggression: {brake}
- Consistency: {consistency}
- Race pace: {pace}
- Aggression: {aggression}
- Tyre management: {tyre}{best_lap_str}{sector_str}

Return a JSON object with exactly these fields:
- "confidence": integer 0-100, your overall confidence rating for this driver
- "confidenceVerdict": short label like "Elite", "Strong", "Developing", "Inconsistent"
- "style": 1-2 sentence description of their driving style
- "strengths": 1-2 sentence summary of key strengths
- "areas": 1-2 sentence summary of areas to watch or improve
- "verdict": 2-3 sentence overall analyst verdict

Return ONLY valid JSON, no markdown fences or extra text."""

    # --- Call Claude ---
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]  # remove opening ```json
            raw = raw.rsplit("```", 1)[0]  # remove closing ```
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned invalid JSON")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"AI API error: {e}")

    return result
