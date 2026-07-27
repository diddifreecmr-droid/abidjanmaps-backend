from abc import ABC, abstractmethod
from datetime import datetime

from app.modules.journeys.domain.entities.journey import (
    Journey,
    JourneyDetail,
    JourneyPosition,
)


class JourneyRepository(ABC):
    @abstractmethod
    async def create(self, journey: Journey) -> Journey:
        raise NotImplementedError

    @abstractmethod
    async def add_positions(
        self,
        journey_id: int,
        positions: list[JourneyPosition],
    ) -> list[JourneyPosition] | None:
        raise NotImplementedError

    @abstractmethod
    async def get_detail(self, journey_id: int, user_id: int) -> JourneyDetail | None:
        raise NotImplementedError

    @abstractmethod
    async def list_for_user(self, user_id: int) -> list[Journey]:
        raise NotImplementedError

    @abstractmethod
    async def finish(
        self,
        journey_id: int,
        user_id: int,
        *,
        finished_at: datetime,
        actual_distance_m: float,
        actual_duration_s: int,
    ) -> Journey | None:
        raise NotImplementedError
