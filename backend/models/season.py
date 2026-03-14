from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    races = relationship("Race", back_populates="season")
