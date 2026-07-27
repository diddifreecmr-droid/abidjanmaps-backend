from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.persistence.base import Base


class JourneyORM(Base):
    __tablename__ = "journeys"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started', 'finished', 'cancelled')",
            name="ck_journeys_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    profile: Mapped[str] = mapped_column(String(30), nullable=False, default="car")
    start_location: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )
    end_location: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )
    planned_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_route_geometry: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actual_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class JourneyPositionORM(Base):
    __tablename__ = "journey_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journey_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
