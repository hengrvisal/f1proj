from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class QualifyingResult(Base):
    __tablename__ = "qualifying_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("constructors.id"), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer)
    q1_ms: Mapped[int | None] = mapped_column(Integer)
    q2_ms: Mapped[int | None] = mapped_column(Integer)
    q3_ms: Mapped[int | None] = mapped_column(Integer)

    race = relationship("Race", back_populates="qualifying_results")
    driver = relationship("Driver", back_populates="qualifying_results")
    constructor = relationship("Constructor", back_populates="qualifying_results")

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_qualifying_result"),
    )
