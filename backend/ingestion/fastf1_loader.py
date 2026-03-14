"""FastF1 session loader with caching."""

import logging
import os

import fastf1

from backend.config import settings

logger = logging.getLogger(__name__)

_cache_enabled = False


def ensure_cache():
    global _cache_enabled
    if not _cache_enabled:
        cache_dir = settings.fastf1_cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)
        _cache_enabled = True


def load_session(year: int, round_num: int, session_type: str):
    """Load a FastF1 session.

    session_type: 'R', 'Q', 'S', 'FP1', 'FP2', 'FP3', etc.
    Returns the FastF1 Session object with laps loaded.
    """
    ensure_cache()
    type_map = {
        "R": "R", "Q": "Q", "S": "S",
        "FP1": "FP1", "FP2": "FP2", "FP3": "FP3",
    }
    ff1_type = type_map.get(session_type, session_type)
    logger.info("Loading FastF1 session: %d R%d %s", year, round_num, ff1_type)

    try:
        sess = fastf1.get_session(year, round_num, ff1_type)
        sess.load()
        return sess
    except Exception as e:
        logger.error("Failed to load FastF1 session %d R%d %s: %s", year, round_num, ff1_type, e)
        return None
