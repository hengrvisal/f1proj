from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    session_type: Mapped[str] = mapped_column(String(20), nullable=False)  # FP1, FP2, FP3, Q, S, R
    date: Mapped[str | None] = mapped_column(DateTime)
    openf1_session_key: Mapped[int | None] = mapped_column(Integer)

    race = relationship("Race", back_populates="sessions")
    laps = relationship("Lap", back_populates="session")
    weather = relationship("Weather", back_populates="session")
    telemetry_samples = relationship("TelemetrySample", back_populates="session")
    race_control_messages = relationship("RaceControlMessage", back_populates="session")
    team_radios = relationship("TeamRadio", back_populates="session")
    tyre_stints = relationship("TyreStint", back_populates="session")
