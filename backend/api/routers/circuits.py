"""Circuit endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_db

router = APIRouter(prefix="/api/circuits", tags=["circuits"])


@router.get("/{circuit_id}/corners")
def get_circuit_corners(circuit_id: int, db: Session = Depends(get_db)):
    """Corner definitions for track map."""
    rows = db.execute(text("""
        SELECT cc.corner_number, cc.entry_distance_m, cc.apex_distance_m, cc.exit_distance_m,
               cc.entry_speed_median, cc.apex_speed_median, cc.exit_speed_median, cc.corner_type
        FROM circuit_corners cc
        WHERE cc.circuit_id = :cid
        ORDER BY cc.corner_number
    """), {"cid": circuit_id}).fetchall()

    circuit = db.execute(text("""
        SELECT name, location, country FROM circuits WHERE id = :cid
    """), {"cid": circuit_id}).fetchone()

    return {
        "circuit_id": circuit_id,
        "name": circuit[0] if circuit else None,
        "location": circuit[1] if circuit else None,
        "country": circuit[2] if circuit else None,
        "corners": [
            {
                "corner_number": r[0], "entry_distance_m": r[1],
                "apex_distance_m": r[2], "exit_distance_m": r[3],
                "entry_speed_median": r[4], "apex_speed_median": r[5],
                "exit_speed_median": r[6], "corner_type": r[7],
            }
            for r in rows
        ],
    }
