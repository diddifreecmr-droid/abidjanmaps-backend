from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.shared.presentation.schemas.geo import GeoPointSchema


class PlaceCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=80)
    location: GeoPointSchema
    aliases: list[str] = Field(default_factory=list)
    vernacular_name: str | None = None
    description: str | None = None
    extra_metadata: dict = Field(default_factory=dict)


class PlaceReadSchema(PlaceCreateSchema):
    id: int
    verified: bool
    validation_status: str = Field(pattern="^(proposed|validated|rejected)$")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlacePatchSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    location: GeoPointSchema | None = None
    aliases: list[str] | None = None
    vernacular_name: str | None = None
    description: str | None = None
    extra_metadata: dict | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_a_change(self):
        business_fields = self.model_fields_set - {"note"}
        if not business_fields:
            raise ValueError("At least one place field must be provided")
        required_fields = {
            "name",
            "category",
            "location",
            "aliases",
            "extra_metadata",
        }
        if any(getattr(self, field) is None for field in business_fields & required_fields):
            raise ValueError("Required place fields cannot be null")
        return self
