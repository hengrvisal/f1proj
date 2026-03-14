from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Lap(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap_time_ms: Mapped[int | None] = mapped_column(Integer)
    sector1_ms: Mapped[int | None] = mapped_column(Integer)
    sector2_ms: Mapped[int | None] = mapped_column(Integer)
    sector3_ms: Mapped[int | None] = mapped_column(Integer)
    compound: Mapped[str | None] = mapped_column(String(20))
    tyre_life: Mapped[int | None] = mapped_column(Integer)
    is_pit_in_lap: Mapped[bool | None] = mapped_column(Boolean)
    is_pit_out_lap: Mapped[bool | None] = mapped_column(Boolean)
    is_personal_best: Mapped[bool | None] = mapped_column(Boolean)
    position: Mapped[int | None] = mapped_column(Integer)
    speed_trap: Mapped[float | None] = mapped_column(Float)

    session = relationship("Session", back_populates="laps")
    driver = relationship("Driver", back_populates="laps")

    __table_args__ = (
        UniqueConstraint("session_id", "driver_id", "lap_number", name="uq_lap"),
    )
