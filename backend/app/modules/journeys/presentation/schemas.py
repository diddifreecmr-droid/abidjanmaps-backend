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
    journey_id: int
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
