from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class TeamRadio(Base):
    __tablename__ = "team_radio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    timestamp: Mapped[str | None] = mapped_column(DateTime)
    recording_url: Mapped[str | None] = mapped_column(Text)

    session = relationship("Session", back_populates="team_radios")
    driver = relationship("Driver", back_populates="team_radios")
