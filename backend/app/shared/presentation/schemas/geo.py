from pydantic import BaseModel, Field


class GeoPointSchema(BaseModel):
    lng: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)


class GeoLineStringSchema(BaseModel):
    type: str = "LineString"
    coordinates: list[list[float]]
