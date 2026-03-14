from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class MlRun(Base):
    __tablename__ = "ml_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    parameters: Mapped[str | None] = mapped_column(Text)  # JSON
    metrics: Mapped[str | None] = mapped_column(Text)  # JSON
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[str | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
