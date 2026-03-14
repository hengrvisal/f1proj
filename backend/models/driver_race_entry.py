from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class DriverRaceEntry(Base):
    __tablename__ = "driver_race_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("constructors.id"), nullable=False)
    driver_number: Mapped[int] = mapped_column(Integer, nullable=False)

    race = relationship("Race", back_populates="driver_race_entries")
    driver = relationship("Driver", back_populates="race_entries")
    constructor = relationship("Constructor", back_populates="race_entries")

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_driver_race_entry"),
    )
