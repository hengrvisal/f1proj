from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class PitStop(Base):
    __tablename__ = "pit_stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    stop_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    total_time_ms: Mapped[int | None] = mapped_column(Integer)

    race = relationship("Race", back_populates="pit_stops")
    driver = relationship("Driver", back_populates="pit_stops")

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", "stop_number", name="uq_pit_stop"),
    )
