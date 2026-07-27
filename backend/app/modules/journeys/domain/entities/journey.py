from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


JOURNEY_STATUSES = frozenset({"started", "finished", "cancelled"})


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
