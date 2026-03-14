from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class RaceResult(Base):
    __tablename__ = "race_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("constructors.id"), nullable=False)
    grid_position: Mapped[int | None] = mapped_column(Integer)
    finish_position: Mapped[int | None] = mapped_column(Integer)
    position_text: Mapped[str | None] = mapped_column(String(10))
    points: Mapped[float | None] = mapped_column(Float)
    laps_completed: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(100))
    time_ms: Mapped[int | None] = mapped_column(Integer)  # race time in ms
    fastest_lap_time_ms: Mapped[int | None] = mapped_column(Integer)
    fastest_lap_number: Mapped[int | None] = mapped_column(Integer)

    race = relationship("Race", back_populates="race_results")
    driver = relationship("Driver", back_populates="race_results")
    constructor = relationship("Constructor", back_populates="race_results")

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_race_result"),
    )
