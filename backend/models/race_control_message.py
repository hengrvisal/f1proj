from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class RaceControlMessage(Base):
    __tablename__ = "race_control_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    timestamp: Mapped[str | None] = mapped_column(DateTime)
    lap_number: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(50))
    flag: Mapped[str | None] = mapped_column(String(50))
    message: Mapped[str | None] = mapped_column(Text)
    driver_number: Mapped[int | None] = mapped_column(Integer)

    session = relationship("Session", back_populates="race_control_messages")
