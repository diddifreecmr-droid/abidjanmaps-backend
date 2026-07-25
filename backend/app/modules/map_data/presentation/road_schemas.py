from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.map_data.domain.taxonomy import (
    normalize_road_surface_state,
    normalize_point_controle,
    normalize_seasonal_practicability,
    normalize_type_flux,
)
from app.shared.presentation.schemas.geo import GeoLineStringSchema
from app.shared.domain.vehicle import normalize_vehicle_profiles


class RoadCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geometry: GeoLineStringSchema
    surface_state: str = Field(min_length=1, max_length=80)
    seasonal_practicability: str = Field(min_length=1, max_length=80)
    surface_reel: str | None = None
    tonnage_max_reel_t: float | None = None
    point_controle: str | None = None
    temps_attente_p50_s: int | None = Field(default=None, ge=0)
    temps_attente_p90_s: int | None = Field(default=None, ge=0)
    eclairage: int | None = Field(default=None, ge=0, le=5)
    securite_nuit: int | None = Field(default=None, ge=0, le=5)
    width_usable_m: float | None = None
    pente_max_pct: float | None = None
    type_flux: str | None = None
    allowed_vehicle_profiles: list[str] = Field(
        default_factory=lambda: ["car", "motorcycle", "truck"]
    )
    is_blocked: bool = False
    extra_metadata: dict = Field(default_factory=dict)

    @field_validator("surface_state")
    @classmethod
    def normalize_surface_state(cls, value: str) -> str:
        return normalize_road_surface_state(value)

    @field_validator("seasonal_practicability")
    @classmethod
    def normalize_seasonal_practicability(cls, value: str) -> str:
        return normalize_seasonal_practicability(value)

    @field_validator("point_controle")
    @classmethod
    def normalize_point_controle(cls, value: str | None) -> str | None:
        return normalize_point_controle(value)

    @field_validator("type_flux")
    @classmethod
    def normalize_type_flux(cls, value: str | None) -> str | None:
        return normalize_type_flux(value)

    @field_validator("allowed_vehicle_profiles")
    @classmethod
    def normalize_vehicle_profiles(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one vehicle profile must be allowed")
        return normalize_vehicle_profiles(value)


class RoadReadSchema(RoadCreateSchema):
    id: int
    validation_status: str = Field(pattern="^(proposed|validated|rejected)$")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoadPatchSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    geometry: GeoLineStringSchema | None = None
    surface_state: str | None = Field(default=None, min_length=1, max_length=80)
    seasonal_practicability: str | None = Field(
        default=None, min_length=1, max_length=80
    )
    surface_reel: str | None = None
    tonnage_max_reel_t: float | None = None
    point_controle: str | None = None
    temps_attente_p50_s: int | None = Field(default=None, ge=0)
    temps_attente_p90_s: int | None = Field(default=None, ge=0)
    eclairage: int | None = Field(default=None, ge=0, le=5)
    securite_nuit: int | None = Field(default=None, ge=0, le=5)
    width_usable_m: float | None = None
    pente_max_pct: float | None = None
    type_flux: str | None = None
    allowed_vehicle_profiles: list[str] | None = None
    is_blocked: bool | None = None
    extra_metadata: dict | None = None
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("surface_state")
    @classmethod
    def normalize_surface_state(cls, value: str | None) -> str | None:
        return normalize_road_surface_state(value) if value is not None else None

    @field_validator("seasonal_practicability")
    @classmethod
    def normalize_seasonal_practicability(cls, value: str | None) -> str | None:
        return normalize_seasonal_practicability(value) if value is not None else None

    @field_validator("point_controle")
    @classmethod
    def normalize_point_controle(cls, value: str | None) -> str | None:
        return normalize_point_controle(value)

    @field_validator("type_flux")
    @classmethod
    def normalize_type_flux(cls, value: str | None) -> str | None:
        return normalize_type_flux(value)

    @field_validator("allowed_vehicle_profiles")
    @classmethod
    def normalize_vehicle_profiles(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("At least one vehicle profile must be allowed")
        return normalize_vehicle_profiles(value)

    @model_validator(mode="after")
    def require_a_change(self):
        business_fields = self.model_fields_set - {"note"}
        if not business_fields:
            raise ValueError("At least one road field must be provided")
        required_fields = {
            "name",
            "geometry",
            "surface_state",
            "seasonal_practicability",
            "extra_metadata",
            "allowed_vehicle_profiles",
        }
        if any(getattr(self, field) is None for field in business_fields & required_fields):
            raise ValueError("Required road fields cannot be null")
        return self
