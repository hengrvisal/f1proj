from sqlalchemy import Float, ForeignKey, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class TelemetrySample(Base):
    __tablename__ = "telemetry_samples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)  # 10m intervals
    speed: Mapped[float | None] = mapped_column(Float)          # km/h
    throttle: Mapped[int | None] = mapped_column(SmallInteger)   # 0-100
    brake: Mapped[bool | None] = mapped_column()                 # boolean
    gear: Mapped[int | None] = mapped_column(SmallInteger)       # 0-8
    rpm: Mapped[int | None] = mapped_column(Integer)
    drs: Mapped[int | None] = mapped_column(SmallInteger)        # DRS status
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)

    session = relationship("Session", back_populates="telemetry_samples")
    driver = relationship("Driver", back_populates="telemetry_samples")

    __table_args__ = (
        UniqueConstraint(
            "session_id", "driver_id", "lap_number", "distance_m",
            name="uq_telemetry_sample",
        ),
    )
