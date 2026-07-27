from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt

from app.modules.journeys.application.ports.journey_repository import JourneyRepository
from app.modules.journeys.domain.entities.journey import (
    Journey,
    JourneyDetail,
    JourneyPosition,
)


class JourneyNotFoundError(Exception):
    pass


class JourneyNotStartedError(Exception):
    pass


class JourneyService:
    def __init__(self, repository: JourneyRepository) -> None:
        self.repository = repository

    async def start_journey(self, journey: Journey) -> Journey:
        return await self.repository.create(journey)

    async def add_positions(
        self,
        *,
        journey_id: int,
        user_id: int,
        positions: list[JourneyPosition],
    ) -> list[JourneyPosition]:
        detail = await self.repository.get_detail(journey_id, user_id)
        if detail is None:
            raise JourneyNotFoundError("Journey not found")
        if detail.journey.status != "started":
            raise JourneyNotStartedError("Journey is not accepting positions")
        saved = await self.repository.add_positions(journey_id, positions)
        if saved is None:
            raise JourneyNotFoundError("Journey not found")
        return saved

    async def finish_journey(
        self,
        *,
        journey_id: int,
        user_id: int,
        finished_at: datetime | None = None,
    ) -> Journey:
        detail = await self.repository.get_detail(journey_id, user_id)
        if detail is None:
            raise JourneyNotFoundError("Journey not found")
        if detail.journey.status != "started":
            raise JourneyNotStartedError("Journey is not started")

        final_finished_at = _ensure_aware(finished_at or datetime.now(timezone.utc))
        started_at = _ensure_aware(detail.journey.started_at or final_finished_at)
        actual_duration_s = max(int((final_finished_at - started_at).total_seconds()), 0)
        actual_distance_m = _total_distance_m(detail.positions)
        finished = await self.repository.finish(
            journey_id,
            user_id,
            finished_at=final_finished_at,
            actual_distance_m=actual_distance_m,
            actual_duration_s=actual_duration_s,
        )
        if finished is None:
            raise JourneyNotFoundError("Journey not found")
        return finished

    async def get_journey(self, *, journey_id: int, user_id: int) -> JourneyDetail:
        detail = await self.repository.get_detail(journey_id, user_id)
        if detail is None:
            raise JourneyNotFoundError("Journey not found")
        return detail

    async def list_journeys(self, *, user_id: int) -> list[Journey]:
        return await self.repository.list_for_user(user_id)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _total_distance_m(positions: list[JourneyPosition]) -> float:
    if len(positions) < 2:
        return 0.0
    ordered = sorted(
        positions,
        key=lambda position: (
            position.recorded_at or datetime.min.replace(tzinfo=timezone.utc),
            position.id or 0,
        ),
    )
    return round(
        sum(
            _distance_m(
                ordered[index - 1].location["lat"],
                ordered[index - 1].location["lng"],
                ordered[index].location["lat"],
                ordered[index].location["lng"],
            )
            for index in range(1, len(ordered))
        ),
        2,
    )


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_m = 6_371_000
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lng2 - lng1)

    haversine = (
        sin(delta_phi / 2) ** 2
        + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    )
    return earth_radius_m * 2 * atan2(sqrt(haversine), sqrt(1 - haversine))
