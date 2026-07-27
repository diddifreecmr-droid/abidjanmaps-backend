from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.journeys.application.ports.journey_repository import JourneyRepository
from app.modules.journeys.domain.entities.journey import (
    Journey,
    JourneyDetail,
    JourneyPosition,
)
from app.modules.journeys.infrastructure.persistence.mappers import (
    geojson_point_to_location,
    point_to_wkt,
)
from app.modules.journeys.infrastructure.persistence.models import (
    JourneyORM,
    JourneyPositionORM,
)


class SQLAlchemyJourneyRepository(JourneyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, journey: Journey) -> Journey:
        orm = JourneyORM(
            user_id=journey.user_id,
            status=journey.status,
            profile=journey.profile,
            start_location=point_to_wkt(journey.start_location),
            end_location=point_to_wkt(journey.end_location),
            planned_distance_m=journey.planned_distance_m,
            planned_duration_s=journey.planned_duration_s,
            planned_route_geometry=journey.planned_route_geometry,
        )
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return await self._to_domain(orm)

    async def add_positions(
        self,
        journey_id: int,
        positions: list[JourneyPosition],
    ) -> list[JourneyPosition] | None:
        journey = await self._get_orm(journey_id)
        if journey is None:
            return None

        now = datetime.now(timezone.utc)
        items = [
            JourneyPositionORM(
                journey_id=journey_id,
                location=point_to_wkt(position.location),
                accuracy_m=position.accuracy_m,
                speed_mps=position.speed_mps,
                recorded_at=position.recorded_at or now,
            )
            for position in positions
        ]
        self.session.add_all(items)
        await self.session.commit()
        for item in items:
            await self.session.refresh(item)
        return [await self._position_to_domain(item) for item in items]

    async def get_detail(self, journey_id: int, user_id: int) -> JourneyDetail | None:
        journey = await self._get_orm(journey_id, user_id=user_id)
        if journey is None:
            return None
        result = await self.session.execute(
            select(JourneyPositionORM)
            .where(JourneyPositionORM.journey_id == journey_id)
            .order_by(JourneyPositionORM.recorded_at, JourneyPositionORM.id)
        )
        return JourneyDetail(
            journey=await self._to_domain(journey),
            positions=[
                await self._position_to_domain(position)
                for position in result.scalars().all()
            ],
        )

    async def list_for_user(self, user_id: int) -> list[Journey]:
        result = await self.session.execute(
            select(JourneyORM)
            .where(JourneyORM.user_id == user_id)
            .order_by(JourneyORM.id.desc())
        )
        return [await self._to_domain(journey) for journey in result.scalars().all()]

    async def finish(
        self,
        journey_id: int,
        user_id: int,
        *,
        finished_at: datetime,
        actual_distance_m: float,
        actual_duration_s: int,
    ) -> Journey | None:
        journey = await self._get_orm(journey_id, user_id=user_id)
        if journey is None:
            return None
        journey.status = "finished"
        journey.finished_at = finished_at
        journey.actual_distance_m = actual_distance_m
        journey.actual_duration_s = actual_duration_s
        await self.session.commit()
        await self.session.refresh(journey)
        return await self._to_domain(journey)

    async def _get_orm(
        self,
        journey_id: int,
        *,
        user_id: int | None = None,
    ) -> JourneyORM | None:
        statement = select(JourneyORM).where(JourneyORM.id == journey_id)
        if user_id is not None:
            statement = statement.where(JourneyORM.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _to_domain(self, journey: JourneyORM) -> Journey:
        start_geojson = await self.session.scalar(
            select(func.ST_AsGeoJSON(JourneyORM.start_location)).where(
                JourneyORM.id == journey.id
            )
        )
        end_geojson = await self.session.scalar(
            select(func.ST_AsGeoJSON(JourneyORM.end_location)).where(
                JourneyORM.id == journey.id
            )
        )
        return Journey(
            id=journey.id,
            user_id=journey.user_id,
            status=journey.status,
            profile=journey.profile,
            start_location=geojson_point_to_location(start_geojson) or {"lng": 0, "lat": 0},
            end_location=geojson_point_to_location(end_geojson) or {"lng": 0, "lat": 0},
            planned_distance_m=journey.planned_distance_m,
            planned_duration_s=journey.planned_duration_s,
            planned_route_geometry=journey.planned_route_geometry,
            actual_distance_m=journey.actual_distance_m,
            actual_duration_s=journey.actual_duration_s,
            started_at=journey.started_at,
            finished_at=journey.finished_at,
            created_at=journey.created_at,
            updated_at=journey.updated_at,
        )

    async def _position_to_domain(self, position: JourneyPositionORM) -> JourneyPosition:
        geojson = await self.session.scalar(
            select(func.ST_AsGeoJSON(JourneyPositionORM.location)).where(
                JourneyPositionORM.id == position.id
            )
        )
        return JourneyPosition(
            id=position.id,
            journey_id=position.journey_id,
            location=geojson_point_to_location(geojson) or {"lng": 0, "lat": 0},
            accuracy_m=position.accuracy_m,
            speed_mps=position.speed_mps,
            recorded_at=position.recorded_at,
            created_at=position.created_at,
        )
