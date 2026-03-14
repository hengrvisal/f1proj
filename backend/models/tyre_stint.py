from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class TyreStint(Base):
    __tablename__ = "tyre_stints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    stint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    compound: Mapped[str | None] = mapped_column(String(20))
    start_lap: Mapped[int | None] = mapped_column(Integer)
    end_lap: Mapped[int | None] = mapped_column(Integer)
    tyre_age_at_start: Mapped[int | None] = mapped_column(Integer)

    session = relationship("Session", back_populates="tyre_stints")
    driver = relationship("Driver", back_populates="tyre_stints")

    __table_args__ = (
        UniqueConstraint("session_id", "driver_id", "stint_number", name="uq_tyre_stint"),
    )
