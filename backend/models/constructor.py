from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Constructor(Base):
    __tablename__ = "constructors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    constructor_ref: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    nationality: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(Text)

    race_entries = relationship("DriverRaceEntry", back_populates="constructor")
    race_results = relationship("RaceResult", back_populates="constructor")
    qualifying_results = relationship("QualifyingResult", back_populates="constructor")
