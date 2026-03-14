"""MLflow integration for experiment tracking."""

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import MlRun

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def _get_mlflow():
    """Lazy import mlflow — gracefully degrade if MLflow server is unavailable."""
    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        return mlflow
    except Exception:
        return None


@contextmanager
def track_run(db: Session, run_type: str, parameters: dict | None = None):
    """Context manager that tracks an ML pipeline run in both the DB and MLflow."""
    ml_run = MlRun(
        run_type=run_type,
        status="running",
        parameters=json.dumps(parameters) if parameters else None,
    )
    db.add(ml_run)
    db.commit()

    mlflow = _get_mlflow()
    mlflow_run = None

    if mlflow:
        try:
            mlflow.set_experiment(f"f1-{run_type}")
            mlflow_run = mlflow.start_run(run_name=f"{run_type}-{ml_run.id}")
            if parameters:
                mlflow.log_params({k: str(v)[:250] for k, v in parameters.items()})
            ml_run.mlflow_run_id = mlflow_run.info.run_id
            db.commit()
        except Exception:
            logger.warning("MLflow unavailable — tracking to DB only")
            mlflow = None
            mlflow_run = None

    try:
        yield ml_run

        ml_run.status = "completed"
        ml_run.finished_at = datetime.now(timezone.utc)
        db.commit()

        if mlflow and mlflow_run:
            try:
                mlflow.end_run("FINISHED")
            except Exception:
                pass

    except Exception as e:
        ml_run.status = "failed"
        ml_run.error_message = str(e)[:1000]
        ml_run.finished_at = datetime.now(timezone.utc)
        db.commit()

        if mlflow and mlflow_run:
            try:
                mlflow.end_run("FAILED")
            except Exception:
                pass

        raise


def log_metrics(db: Session, ml_run: MlRun, metrics: dict):
    """Log metrics to both DB and MLflow."""
    ml_run.metrics = json.dumps(metrics)
    db.commit()

    mlflow = _get_mlflow()
    if mlflow:
        try:
            mlflow.log_metrics({k: float(v) for k, v in metrics.items() if v is not None})
        except Exception:
            logger.warning("Failed to log metrics to MLflow")
