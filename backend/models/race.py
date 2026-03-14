from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Race(Base):
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    circuit_id: Mapped[int] = mapped_column(ForeignKey("circuits.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[str | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
    openf1_meeting_key: Mapped[int | None] = mapped_column(Integer)

    season = relationship("Season", back_populates="races")
    circuit = relationship("Circuit", back_populates="races")
    sessions = relationship("Session", back_populates="race")
    driver_race_entries = relationship("DriverRaceEntry", back_populates="race")
    race_results = relationship("RaceResult", back_populates="race")
    qualifying_results = relationship("QualifyingResult", back_populates="race")
    pit_stops = relationship("PitStop", back_populates="race")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
