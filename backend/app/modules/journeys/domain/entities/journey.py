from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


JOURNEY_STATUSES = frozenset({"started", "finished", "cancelled"})
MAP_TRACE_INSIGHT_STATUSES = frozenset({"proposed", "validated", "rejected"})


@dataclass(frozen=True, kw_only=True)
class Journey:
    id: int | None = None
    user_id: int
    status: str = "started"
    profile: str = "car"
    start_location: dict[str, float]
    end_location: dict[str, float]
    planned_distance_m: int | None = None
    planned_duration_s: int | None = None
    planned_route_geometry: dict[str, Any] | None = None
    actual_distance_m: float | None = None
    actual_duration_s: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status not in JOURNEY_STATUSES:
            raise ValueError(f"Unsupported journey status: {self.status}")


@dataclass(frozen=True, kw_only=True)
class JourneyPosition:
    id: int | None = None
    journey_id: int
    location: dict[str, float]
    accuracy_m: float | None = None
    speed_mps: float | None = None
    recorded_at: datetime | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class JourneyDetail:
    journey: Journey
    positions: list[JourneyPosition] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class JourneyAnalysis:
    id: int | None = None
    journey_id: int
    status: str = "analyzed"
    points_count: int
    usable_points_count: int
    quality_score: float
    quality_label: str
    actual_distance_m: float
    actual_duration_s: int
    average_speed_kmh: float
    phone_average_speed_kmh: float | None = None
    moving_time_s: int = 0
    stopped_time_s: int = 0
    max_speed_kmh: float = 0.0
    gps_gap_count: int = 0
    suspicious_jump_count: int = 0
    planned_distance_m: int | None = None
    planned_duration_s: int | None = None
    distance_delta_m: float | None = None
    duration_delta_s: int | None = None
    duration_ratio: float | None = None
    detected_events: list[dict[str, Any]] = field(default_factory=list)
    recommendation: str = "ok"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class MapTraceInsight:
    id: int | None = None
    journey_id: int
    analysis_id: int
    insight_type: str
    severity: int
    confidence_score: float
    message: str
    geometry: dict[str, Any] | None = None
    duplicate_key: str | None = None
    evidence_count: int = 1
    latest_evidence_trace_id: int | None = None
    status: str = "proposed"
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status not in MAP_TRACE_INSIGHT_STATUSES:
            raise ValueError(f"Unsupported map trace insight status: {self.status}")
