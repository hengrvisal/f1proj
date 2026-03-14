from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_ref: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(10))
    permanent_number: Mapped[int | None] = mapped_column(Integer)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[str | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(Text)

    race_entries = relationship("DriverRaceEntry", back_populates="driver")
    laps = relationship("Lap", back_populates="driver")
    pit_stops = relationship("PitStop", back_populates="driver")
    tyre_stints = relationship("TyreStint", back_populates="driver")
    telemetry_samples = relationship("TelemetrySample", back_populates="driver")
    race_results = relationship("RaceResult", back_populates="driver")
    qualifying_results = relationship("QualifyingResult", back_populates="driver")
    team_radios = relationship("TeamRadio", back_populates="driver")
