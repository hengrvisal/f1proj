from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class CircuitCorner(Base):
    __tablename__ = "circuit_corners"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    circuit_id: Mapped[int] = mapped_column(ForeignKey("circuits.id"), nullable=False)
    corner_number: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    apex_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    exit_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    entry_speed_median: Mapped[float | None] = mapped_column(Float)
    apex_speed_median: Mapped[float | None] = mapped_column(Float)
    exit_speed_median: Mapped[float | None] = mapped_column(Float)
    corner_type: Mapped[str | None] = mapped_column(String(20))  # slow/medium/fast

    circuit = relationship("Circuit")

    __table_args__ = (
        UniqueConstraint("circuit_id", "corner_number", name="uq_circuit_corner"),
    )
