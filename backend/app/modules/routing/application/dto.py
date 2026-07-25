from dataclasses import dataclass


@dataclass(frozen=True)
class RouteRequestDTO:
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    profile: str
