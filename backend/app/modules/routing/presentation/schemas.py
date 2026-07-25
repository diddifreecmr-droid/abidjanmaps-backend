from pydantic import BaseModel, Field, field_validator

from app.shared.domain.vehicle import normalize_vehicle_profile


class CoordinateSchema(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class RouteRequestSchema(BaseModel):
    start: CoordinateSchema
    end: CoordinateSchema
    profile: str = Field(default="car")
    vehicle_width_m: float | None = Field(default=None, gt=0, le=5)
    vehicle_weight_t: float | None = Field(default=None, gt=0, le=100)

    @field_validator("profile")
    @classmethod
    def normalize_profile(cls, value: str) -> str:
        return normalize_vehicle_profile(value)


class RouteGeometrySchema(BaseModel):
    type: str
    coordinates: list[list[float]]


class RouteSchema(BaseModel):
    geometry: RouteGeometrySchema
    distance_m: int
    duration_s: int


class PriceSchema(BaseModel):
    amount: int
    currency: str = "XOF"


class RouteResponseSchema(BaseModel):
    status: str
    route: RouteSchema
    price: PriceSchema


class RouteProposalSchema(BaseModel):
    route: RouteSchema
    price: PriceSchema
    score: float
    rank: int
    score_breakdown: dict
    enrichment: dict | None = None


class RouteProposalResponseSchema(BaseModel):
    status: str
    proposals: list[RouteProposalSchema]


class RouteProposalDetailResponseSchema(RouteProposalResponseSchema):
    pass
