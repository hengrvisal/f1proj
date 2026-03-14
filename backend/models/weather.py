from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Weather(Base):
    __tablename__ = "weather"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    timestamp: Mapped[str | None] = mapped_column(DateTime)
    air_temp: Mapped[float | None] = mapped_column(Float)
    track_temp: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    pressure: Mapped[float | None] = mapped_column(Float)
    wind_speed: Mapped[float | None] = mapped_column(Float)
    wind_direction: Mapped[int | None] = mapped_column(Integer)
    rainfall: Mapped[bool | None] = mapped_column(Boolean)

    session = relationship("Session", back_populates="weather")
