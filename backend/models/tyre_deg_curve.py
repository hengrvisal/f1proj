from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class TyreDegCurve(Base):
    __tablename__ = "tyre_deg_curves"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    stint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    compound: Mapped[str | None] = mapped_column(String(20))
    model_type: Mapped[str | None] = mapped_column(String(20))  # linear/quadratic
    coefficients: Mapped[str | None] = mapped_column(Text)  # JSON
    r_squared: Mapped[float | None] = mapped_column(Float)
    deg_rate_ms_per_lap: Mapped[float | None] = mapped_column(Float)
    predicted_cliff_lap: Mapped[int | None] = mapped_column(Integer)
    num_laps: Mapped[int | None] = mapped_column(Integer)

    session = relationship("Session")
    driver = relationship("Driver")

    __table_args__ = (
        UniqueConstraint("session_id", "driver_id", "stint_number", name="uq_tyre_deg_curve"),
    )
