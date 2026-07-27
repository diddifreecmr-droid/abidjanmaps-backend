from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.journeys.application.ports.journey_repository import JourneyRepository
from app.modules.journeys.domain.entities.journey import (
    JourneyAnalysis,
    Journey,
    JourneyDetail,
    JourneyPosition,
    MapTraceInsight,
)
from app.modules.journeys.infrastructure.persistence.mappers import (
    geojson_point_to_location,
    point_to_wkt,
)
from app.modules.journeys.infrastructure.persistence.models import (
    JourneyAnalysisORM,
    JourneyORM,
    JourneyPositionORM,
    MapTraceInsightORM,
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
        return await self._detail_from_orm(journey, journey_id)

    async def get_detail_for_admin(self, journey_id: int) -> JourneyDetail | None:
        journey = await self._get_orm(journey_id)
        return await self._detail_from_orm(journey, journey_id)

    async def _detail_from_orm(
        self,
        journey: JourneyORM | None,
        journey_id: int,
    ) -> JourneyDetail | None:
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

    async def save_analysis(
        self,
        journey_id: int,
        user_id: int,
        analysis: JourneyAnalysis,
    ) -> JourneyAnalysis | None:
        journey = await self._get_orm(journey_id, user_id=user_id)
        if journey is None:
            return None

        result = await self.session.execute(
            select(JourneyAnalysisORM).where(JourneyAnalysisORM.journey_id == journey_id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            orm = JourneyAnalysisORM(journey_id=journey_id)
            self.session.add(orm)

        orm.status = analysis.status
        orm.points_count = analysis.points_count
        orm.usable_points_count = analysis.usable_points_count
        orm.quality_score = analysis.quality_score
        orm.quality_label = analysis.quality_label
        orm.actual_distance_m = analysis.actual_distance_m
        orm.actual_duration_s = analysis.actual_duration_s
        orm.average_speed_kmh = analysis.average_speed_kmh
        orm.phone_average_speed_kmh = analysis.phone_average_speed_kmh
        orm.moving_time_s = analysis.moving_time_s
        orm.stopped_time_s = analysis.stopped_time_s
        orm.max_speed_kmh = analysis.max_speed_kmh
        orm.gps_gap_count = analysis.gps_gap_count
        orm.suspicious_jump_count = analysis.suspicious_jump_count
        orm.planned_distance_m = analysis.planned_distance_m
        orm.planned_duration_s = analysis.planned_duration_s
        orm.distance_delta_m = analysis.distance_delta_m
        orm.duration_delta_s = analysis.duration_delta_s
        orm.duration_ratio = analysis.duration_ratio
        orm.detected_events = analysis.detected_events
        orm.recommendation = analysis.recommendation
        await self.session.commit()
        await self.session.refresh(orm)
        return self._analysis_to_domain(orm)

    async def get_analysis(
        self,
        journey_id: int,
        user_id: int,
    ) -> JourneyAnalysis | None:
        journey = await self._get_orm(journey_id, user_id=user_id)
        if journey is None:
            return None
        result = await self.session.execute(
            select(JourneyAnalysisORM).where(JourneyAnalysisORM.journey_id == journey_id)
        )
        analysis = result.scalar_one_or_none()
        if analysis is None:
            return None
        return self._analysis_to_domain(analysis)

    async def replace_proposed_insights(
        self,
        analysis_id: int,
        insights: list[MapTraceInsight],
    ) -> list[MapTraceInsight]:
        await self.session.execute(
            delete(MapTraceInsightORM).where(
                MapTraceInsightORM.analysis_id == analysis_id,
                MapTraceInsightORM.status == "proposed",
            )
        )
        filtered_insights = await self._filter_duplicate_insights(analysis_id, insights)
        items = [
            MapTraceInsightORM(
                journey_id=insight.journey_id,
                analysis_id=analysis_id,
                insight_type=insight.insight_type,
                severity=insight.severity,
                confidence_score=insight.confidence_score,
                message=insight.message,
                geometry=insight.geometry,
                duplicate_key=insight.duplicate_key,
                evidence_count=insight.evidence_count,
                latest_evidence_trace_id=insight.latest_evidence_trace_id,
                status=insight.status,
            )
            for insight in filtered_insights
        ]
        self.session.add_all(items)
        await self.session.commit()
        for item in items:
            await self.session.refresh(item)
        return [self._insight_to_domain(item) for item in items]

    async def _filter_duplicate_insights(
        self,
        analysis_id: int,
        insights: list[MapTraceInsight],
    ) -> list[MapTraceInsight]:
        duplicate_keys = [
            insight.duplicate_key
            for insight in insights
            if insight.duplicate_key is not None
        ]
        existing_by_key: dict[str, MapTraceInsightORM] = {}
        if duplicate_keys:
            result = await self.session.execute(
                select(MapTraceInsightORM).where(
                    MapTraceInsightORM.duplicate_key.in_(duplicate_keys),
                    MapTraceInsightORM.status.in_(["proposed", "validated"]),
                    MapTraceInsightORM.analysis_id != analysis_id,
                )
            )
            existing_by_key = {
                item.duplicate_key: item
                for item in result.scalars().all()
                if item.duplicate_key is not None
            }

        accepted: list[MapTraceInsight] = []
        seen_keys: set[str] = set()
        updated_existing_keys: set[str] = set()
        for insight in insights:
            key = insight.duplicate_key
            if key is not None and key in existing_by_key:
                if key not in updated_existing_keys:
                    existing = existing_by_key[key]
                    if existing.journey_id != insight.journey_id:
                        existing.evidence_count = max(existing.evidence_count, 1) + 1
                        existing.latest_evidence_trace_id = insight.journey_id
                        existing.severity = max(existing.severity, insight.severity)
                        existing.confidence_score = max(
                            existing.confidence_score,
                            insight.confidence_score,
                        )
                    updated_existing_keys.add(key)
                continue
            if key is not None and key in seen_keys:
                continue
            if key is not None:
                seen_keys.add(key)
            accepted.append(insight)
        return accepted

    async def list_insights(
        self,
        status: str | None = None,
        insight_type: str | None = None,
        severity_min: int | None = None,
        trace_id: int | None = None,
    ) -> list[MapTraceInsight]:
        statement = select(MapTraceInsightORM).order_by(MapTraceInsightORM.id.desc())
        if status is not None:
            statement = statement.where(MapTraceInsightORM.status == status)
        if insight_type is not None:
            statement = statement.where(MapTraceInsightORM.insight_type == insight_type)
        if severity_min is not None:
            statement = statement.where(MapTraceInsightORM.severity >= severity_min)
        if trace_id is not None:
            statement = statement.where(MapTraceInsightORM.journey_id == trace_id)
        result = await self.session.execute(statement)
        return [self._insight_to_domain(item) for item in result.scalars().all()]

    async def get_insight(self, insight_id: int) -> MapTraceInsight | None:
        result = await self.session.execute(
            select(MapTraceInsightORM).where(MapTraceInsightORM.id == insight_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None
        return self._insight_to_domain(item)

    async def review_insight(
        self,
        insight_id: int,
        *,
        status: str,
        reviewed_by: int,
        review_note: str | None,
        reviewed_at: datetime,
    ) -> MapTraceInsight | None:
        result = await self.session.execute(
            select(MapTraceInsightORM).where(MapTraceInsightORM.id == insight_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None
        item.status = status
        item.reviewed_by = reviewed_by
        item.reviewed_at = reviewed_at
        item.review_note = review_note
        await self.session.commit()
        await self.session.refresh(item)
        return self._insight_to_domain(item)

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

    def _analysis_to_domain(self, analysis: JourneyAnalysisORM) -> JourneyAnalysis:
        return JourneyAnalysis(
            id=analysis.id,
            journey_id=analysis.journey_id,
            status=analysis.status,
            points_count=analysis.points_count,
            usable_points_count=analysis.usable_points_count,
            quality_score=analysis.quality_score,
            quality_label=analysis.quality_label,
            actual_distance_m=analysis.actual_distance_m,
            actual_duration_s=analysis.actual_duration_s,
            average_speed_kmh=analysis.average_speed_kmh,
            phone_average_speed_kmh=analysis.phone_average_speed_kmh,
            moving_time_s=getattr(analysis, "moving_time_s", 0),
            stopped_time_s=getattr(analysis, "stopped_time_s", 0),
            max_speed_kmh=getattr(analysis, "max_speed_kmh", 0.0),
            gps_gap_count=getattr(analysis, "gps_gap_count", 0),
            suspicious_jump_count=getattr(analysis, "suspicious_jump_count", 0),
            planned_distance_m=analysis.planned_distance_m,
            planned_duration_s=analysis.planned_duration_s,
            distance_delta_m=analysis.distance_delta_m,
            duration_delta_s=analysis.duration_delta_s,
            duration_ratio=analysis.duration_ratio,
            detected_events=analysis.detected_events or [],
            recommendation=analysis.recommendation,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )

    def _insight_to_domain(self, insight: MapTraceInsightORM) -> MapTraceInsight:
        return MapTraceInsight(
            id=insight.id,
            journey_id=insight.journey_id,
            analysis_id=insight.analysis_id,
            insight_type=insight.insight_type,
            severity=insight.severity,
            confidence_score=insight.confidence_score,
            message=insight.message,
            geometry=insight.geometry,
            duplicate_key=insight.duplicate_key,
            evidence_count=getattr(insight, "evidence_count", 1),
            latest_evidence_trace_id=getattr(
                insight,
                "latest_evidence_trace_id",
                None,
            ),
            status=insight.status,
            reviewed_by=insight.reviewed_by,
            reviewed_at=insight.reviewed_at,
            review_note=insight.review_note,
            created_at=insight.created_at,
            updated_at=insight.updated_at,
        )
