from sqlalchemy import Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class DriverSimilarity(Base):
    __tablename__ = "driver_similarities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_a_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    driver_b_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    cosine_similarity: Mapped[float] = mapped_column(Float, nullable=False)

    driver_a = relationship("Driver", foreign_keys=[driver_a_id])
    driver_b = relationship("Driver", foreign_keys=[driver_b_id])
    season = relationship("Season")

    __table_args__ = (
        UniqueConstraint("driver_a_id", "driver_b_id", "season_id", name="uq_driver_similarity"),
    )
