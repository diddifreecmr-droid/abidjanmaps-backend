from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.shared.presentation.schemas.geo import GeoPointSchema
from app.modules.local_enrichment.domain.taxonomy import normalize_route_report_type


class RouteReportCreateSchema(BaseModel):
    road_id: int | None = None
    report_type: str = Field(min_length=1, max_length=80)
    severity: int = Field(ge=1, le=5)
    message: str = Field(min_length=1)
    geometry: GeoPointSchema | None = None
    extra_metadata: dict = Field(default_factory=dict)

    @field_validator("report_type")
    @classmethod
    def normalize_report_type(cls, value: str) -> str:
        return normalize_route_report_type(value)


class RouteReportReadSchema(RouteReportCreateSchema):
    id: int
    reported_by: str | None = None
    validation_status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    reported_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RouteReportReviewSchema(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class RouteReportPatchSchema(BaseModel):
    road_id: int | None = None
    report_type: str | None = Field(default=None, min_length=1, max_length=80)
    severity: int | None = Field(default=None, ge=1, le=5)
    message: str | None = Field(default=None, min_length=1)
    geometry: GeoPointSchema | None = None
    extra_metadata: dict | None = None
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("report_type")
    @classmethod
    def normalize_report_type(cls, value: str | None) -> str | None:
        return normalize_route_report_type(value) if value is not None else None

    @model_validator(mode="after")
    def require_a_change(self):
        business_fields = self.model_fields_set - {"note"}
        if not business_fields:
            raise ValueError("At least one route report field must be provided")
        required_fields = {"report_type", "severity", "message", "extra_metadata"}
        if any(getattr(self, field) is None for field in business_fields & required_fields):
            raise ValueError("Required route report fields cannot be null")
        return self
