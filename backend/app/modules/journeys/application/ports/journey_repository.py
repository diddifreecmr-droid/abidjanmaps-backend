from abc import ABC, abstractmethod
from datetime import datetime

from app.modules.journeys.domain.entities.journey import (
    JourneyAnalysis,
    Journey,
    JourneyDetail,
    JourneyPosition,
    MapTraceInsight,
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
    async def get_detail_for_admin(self, journey_id: int) -> JourneyDetail | None:
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

    @abstractmethod
    async def save_analysis(
        self,
        journey_id: int,
        user_id: int,
        analysis: JourneyAnalysis,
    ) -> JourneyAnalysis | None:
        raise NotImplementedError

    @abstractmethod
    async def get_analysis(
        self,
        journey_id: int,
        user_id: int,
    ) -> JourneyAnalysis | None:
        raise NotImplementedError

    @abstractmethod
    async def replace_proposed_insights(
        self,
        analysis_id: int,
        insights: list[MapTraceInsight],
    ) -> list[MapTraceInsight]:
        raise NotImplementedError

    @abstractmethod
    async def list_insights(
        self,
        status: str | None = None,
        insight_type: str | None = None,
        severity_min: int | None = None,
        trace_id: int | None = None,
    ) -> list[MapTraceInsight]:
        raise NotImplementedError

    @abstractmethod
    async def get_insight(self, insight_id: int) -> MapTraceInsight | None:
        raise NotImplementedError

    @abstractmethod
    async def review_insight(
        self,
        insight_id: int,
        *,
        status: str,
        reviewed_by: int,
        review_note: str | None,
        reviewed_at: datetime,
    ) -> MapTraceInsight | None:
        raise NotImplementedError
