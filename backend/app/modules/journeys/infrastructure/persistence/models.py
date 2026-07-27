from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
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


class JourneyAnalysisORM(Base):
    __tablename__ = "journey_analyses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('analyzed')",
            name="ck_journey_analyses_status",
        ),
        CheckConstraint(
            "quality_score >= 0 AND quality_score <= 1",
            name="ck_journey_analyses_quality_score",
        ),
        UniqueConstraint("journey_id", name="uq_journey_analyses_journey_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journey_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="analyzed")
    points_count: Mapped[int] = mapped_column(Integer, nullable=False)
    usable_points_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_label: Mapped[str] = mapped_column(String(20), nullable=False)
    actual_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    actual_duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    average_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    phone_average_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    moving_time_s: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stopped_time_s: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    gps_gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspicious_jump_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_delta_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_delta_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_events: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    recommendation: Mapped[str] = mapped_column(String(40), nullable=False)
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


class MapTraceInsightORM(Base):
    __tablename__ = "map_trace_insights"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'validated', 'rejected')",
            name="ck_map_trace_insights_status",
        ),
        CheckConstraint(
            "severity >= 1 AND severity <= 5",
            name="ck_map_trace_insights_severity",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_map_trace_insights_confidence_score",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journey_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("journey_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insight_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    geometry: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    duplicate_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latest_evidence_trace_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
