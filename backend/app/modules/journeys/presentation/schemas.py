from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.shared.domain.vehicle import normalize_vehicle_profile
from app.shared.presentation.schemas.geo import GeoPointSchema


class JourneyStartSchema(BaseModel):
    start: GeoPointSchema
    end: GeoPointSchema
    profile: str = "car"
    planned_distance_m: int | None = Field(default=None, ge=0)
    planned_duration_s: int | None = Field(default=None, ge=0)
    planned_route_geometry: dict[str, Any] | None = None

    @field_validator("profile")
    @classmethod
    def normalize_profile(cls, value: str) -> str:
        return normalize_vehicle_profile(value)


class JourneyPositionCreateSchema(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    speed_mps: float | None = Field(default=None, ge=0)
    recorded_at: datetime | None = None


class JourneyPositionsBatchSchema(BaseModel):
    positions: list[JourneyPositionCreateSchema] = Field(min_length=1, max_length=500)


class JourneyFinishSchema(BaseModel):
    finished_at: datetime | None = None


class JourneyPositionReadSchema(BaseModel):
    id: int
    trace_id: int
    location: GeoPointSchema
    accuracy_m: float | None = None
    speed_mps: float | None = None
    recorded_at: datetime | None = None
    created_at: datetime | None = None


class JourneyReadSchema(BaseModel):
    id: int
    user_id: int
    status: str
    profile: str
    start: GeoPointSchema
    end: GeoPointSchema
    planned_distance_m: int | None = None
    planned_duration_s: int | None = None
    planned_route_geometry: dict[str, Any] | None = None
    actual_distance_m: float | None = None
    actual_duration_s: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class JourneyDetailReadSchema(JourneyReadSchema):
    positions: list[JourneyPositionReadSchema]


class JourneyAnalysisReadSchema(BaseModel):
    id: int
    trace_id: int
    status: str
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
    detected_events: list[dict[str, Any]]
    recommendation: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MapTraceInsightReadSchema(BaseModel):
    id: int
    trace_id: int
    analysis_id: int
    insight_type: str
    severity: int
    confidence_score: float
    message: str
    geometry: dict[str, Any] | None = None
    duplicate_key: str | None = None
    evidence_count: int = 1
    latest_evidence_trace_id: int | None = None
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MapTraceInsightReviewQueueItemSchema(MapTraceInsightReadSchema):
    review_priority_score: float
    recommended_action: str
    conversion_ready: bool


class MapTraceInsightReviewSchema(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class MapTraceInsightDetailReadSchema(MapTraceInsightReadSchema):
    trace: JourneyDetailReadSchema
    analysis: JourneyAnalysisReadSchema


class MapTraceInsightConversionReadSchema(BaseModel):
    insight: MapTraceInsightReadSchema
    route_report: dict[str, Any]
