from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class DriverDnaFeature(Base):
    __tablename__ = "driver_dna_features"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    feature_vector: Mapped[str | None] = mapped_column(Text)  # JSON
    cluster_id: Mapped[int | None] = mapped_column(Integer)
    cluster_label: Mapped[str | None] = mapped_column(String(100))
    pca_x: Mapped[float | None] = mapped_column(Float)
    pca_y: Mapped[float | None] = mapped_column(Float)
    tsne_x: Mapped[float | None] = mapped_column(Float)
    tsne_y: Mapped[float | None] = mapped_column(Float)

    driver = relationship("Driver")
    season = relationship("Season")

    __table_args__ = (
        UniqueConstraint("driver_id", "season_id", name="uq_driver_dna_feature"),
    )
