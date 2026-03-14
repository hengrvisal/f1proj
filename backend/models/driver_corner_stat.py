from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class DriverCornerStat(Base):
    __tablename__ = "driver_corner_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    corner_id: Mapped[int] = mapped_column(ForeignKey("circuit_corners.id"), nullable=False)
    brake_point_m: Mapped[float | None] = mapped_column(Float)
    min_speed: Mapped[float | None] = mapped_column(Float)
    entry_speed: Mapped[float | None] = mapped_column(Float)
    exit_speed: Mapped[float | None] = mapped_column(Float)
    throttle_on_distance: Mapped[float | None] = mapped_column(Float)
    trail_braking_score: Mapped[float | None] = mapped_column(Float)
    gear_at_apex: Mapped[int | None] = mapped_column(Integer)
    time_in_corner_ms: Mapped[int | None] = mapped_column(Integer)

    session = relationship("Session")
    driver = relationship("Driver")
    corner = relationship("CircuitCorner")

    __table_args__ = (
        UniqueConstraint("session_id", "driver_id", "corner_id", name="uq_driver_corner_stat"),
    )
