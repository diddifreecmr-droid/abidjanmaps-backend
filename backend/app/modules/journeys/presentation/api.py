from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.local_enrichment.application.use_cases.manage_route_reports import (
    RouteReportWorkflow,
)
from app.modules.local_enrichment.domain.entities.route_report import RouteReport
from app.modules.local_enrichment.infrastructure.persistence.route_report_repository import (
    SQLAlchemyRouteReportRepository,
)
from app.modules.journeys.application.use_cases.manage_journeys import (
    InvalidMapTraceInsightStatusError,
    JourneyAnalysisNotFoundError,
    JourneyNotFinishedError,
    JourneyNotFoundError,
    JourneyNotStartedError,
    JourneyService,
    MapTraceInsightNotFoundError,
)
from app.modules.journeys.domain.entities.journey import (
    Journey,
    JourneyAnalysis,
    JourneyDetail,
    JourneyPosition,
    MapTraceInsight,
)
from app.modules.journeys.infrastructure.persistence.journey_repository import (
    SQLAlchemyJourneyRepository,
)
from app.modules.journeys.presentation.schemas import (
    JourneyDetailReadSchema,
    JourneyFinishSchema,
    JourneyAnalysisReadSchema,
    JourneyPositionReadSchema,
    JourneyPositionsBatchSchema,
    JourneyReadSchema,
    JourneyStartSchema,
    MapTraceInsightDetailReadSchema,
    MapTraceInsightConversionReadSchema,
    MapTraceInsightReadSchema,
    MapTraceInsightReviewQueueItemSchema,
    MapTraceInsightReviewSchema,
)
from app.modules.map_data.infrastructure.persistence.road_repository import (
    SQLAlchemyRoadRepository,
)
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user, require_admin
from app.shared.infrastructure.db import get_async_session


router = APIRouter(tags=["map-traces"])

CONVERTIBLE_INSIGHT_REPORT_TYPES = {
    "duration_much_longer_than_planned": "degraded",
    "slow_journey": "degraded",
    "possible_slow_segment": "degraded",
    "possible_blocked_road": "blocked",
    "possible_detour": "degraded",
}
INSIGHT_SORT_FIELDS = frozenset(
    {
        "priority",
        "severity",
        "evidence",
        "confidence",
        "newest",
    }
)
INSIGHT_SORT_ORDERS = frozenset({"asc", "desc"})


def get_journey_service(
    session: AsyncSession = Depends(get_async_session),
) -> JourneyService:
    return JourneyService(SQLAlchemyJourneyRepository(session))


def _route_report_workflow(session: AsyncSession) -> RouteReportWorkflow:
    return RouteReportWorkflow(
        repository=SQLAlchemyRouteReportRepository(session),
        road_history=SQLAlchemyRoadRepository(session),
    )


def _journey_response(journey: Journey) -> JourneyReadSchema:
    if journey.id is None:
        raise RuntimeError("Persisted journey has no identifier")
    return JourneyReadSchema(
        id=journey.id,
        user_id=journey.user_id,
        status=journey.status,
        profile=journey.profile,
        start=journey.start_location,
        end=journey.end_location,
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


def _position_response(position: JourneyPosition) -> JourneyPositionReadSchema:
    if position.id is None:
        raise RuntimeError("Persisted journey position has no identifier")
    return JourneyPositionReadSchema(
        id=position.id,
        trace_id=position.journey_id,
        location=position.location,
        accuracy_m=position.accuracy_m,
        speed_mps=position.speed_mps,
        recorded_at=position.recorded_at,
        created_at=position.created_at,
    )


def _detail_response(detail: JourneyDetail) -> JourneyDetailReadSchema:
    journey = _journey_response(detail.journey)
    return JourneyDetailReadSchema(
        **journey.model_dump(),
        positions=[_position_response(position) for position in detail.positions],
    )


def _analysis_response(analysis: JourneyAnalysis) -> JourneyAnalysisReadSchema:
    if analysis.id is None:
        raise RuntimeError("Persisted journey analysis has no identifier")
    return JourneyAnalysisReadSchema(
        id=analysis.id,
        trace_id=analysis.journey_id,
        status=analysis.status,
        points_count=analysis.points_count,
        usable_points_count=analysis.usable_points_count,
        quality_score=analysis.quality_score,
        quality_label=analysis.quality_label,
        actual_distance_m=analysis.actual_distance_m,
        actual_duration_s=analysis.actual_duration_s,
        average_speed_kmh=analysis.average_speed_kmh,
        phone_average_speed_kmh=analysis.phone_average_speed_kmh,
        moving_time_s=analysis.moving_time_s,
        stopped_time_s=analysis.stopped_time_s,
        max_speed_kmh=analysis.max_speed_kmh,
        gps_gap_count=analysis.gps_gap_count,
        suspicious_jump_count=analysis.suspicious_jump_count,
        planned_distance_m=analysis.planned_distance_m,
        planned_duration_s=analysis.planned_duration_s,
        distance_delta_m=analysis.distance_delta_m,
        duration_delta_s=analysis.duration_delta_s,
        duration_ratio=analysis.duration_ratio,
        detected_events=analysis.detected_events,
        recommendation=analysis.recommendation,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


def _insight_response(insight: MapTraceInsight) -> MapTraceInsightReadSchema:
    if insight.id is None:
        raise RuntimeError("Persisted map trace insight has no identifier")
    return MapTraceInsightReadSchema(
        id=insight.id,
        trace_id=insight.journey_id,
        analysis_id=insight.analysis_id,
        insight_type=insight.insight_type,
        severity=insight.severity,
        confidence_score=insight.confidence_score,
        message=insight.message,
        geometry=insight.geometry,
        duplicate_key=insight.duplicate_key,
        evidence_count=insight.evidence_count,
        latest_evidence_trace_id=insight.latest_evidence_trace_id,
        status=insight.status,
        reviewed_by=insight.reviewed_by,
        reviewed_at=insight.reviewed_at,
        review_note=insight.review_note,
        created_at=insight.created_at,
        updated_at=insight.updated_at,
    )


def _review_priority_score(insight: MapTraceInsight) -> float:
    evidence_score = min(insight.evidence_count, 5) / 5
    severity_score = insight.severity / 5
    confidence_score = insight.confidence_score
    status_bonus = 0.10 if insight.status == "validated" else 0
    return round(
        severity_score * 0.45
        + evidence_score * 0.30
        + confidence_score * 0.25
        + status_bonus,
        3,
    )


def _conversion_ready(
    insight: MapTraceInsight,
    *,
    min_evidence_count: int = 2,
    min_confidence_score: float = 0.6,
    min_severity: int = 3,
) -> bool:
    return (
        insight.status == "validated"
        and insight.insight_type in CONVERTIBLE_INSIGHT_REPORT_TYPES
        and insight.evidence_count >= min_evidence_count
        and insight.confidence_score >= min_confidence_score
        and insight.severity >= min_severity
    )


def _recommended_action(insight: MapTraceInsight) -> str:
    if _conversion_ready(insight):
        return "convert_to_route_report"
    if insight.status == "proposed" and insight.evidence_count >= 2 and insight.severity >= 3:
        return "review_priority"
    if insight.status == "validated" and insight.insight_type not in CONVERTIBLE_INSIGHT_REPORT_TYPES:
        return "keep_for_context"
    if insight.status == "rejected":
        return "no_action"
    return "watch"


def _insight_review_queue_response(
    insight: MapTraceInsight,
) -> MapTraceInsightReviewQueueItemSchema:
    base = _insight_response(insight).model_dump()
    return MapTraceInsightReviewQueueItemSchema(
        **base,
        review_priority_score=_review_priority_score(insight),
        recommended_action=_recommended_action(insight),
        conversion_ready=_conversion_ready(insight),
    )


def _sort_insights(
    insights: list[MapTraceInsight],
    *,
    sort: str,
    order: str,
) -> list[MapTraceInsight]:
    if sort not in INSIGHT_SORT_FIELDS:
        raise HTTPException(status_code=422, detail=f"Unsupported sort: {sort}")
    if order not in INSIGHT_SORT_ORDERS:
        raise HTTPException(status_code=422, detail=f"Unsupported order: {order}")
    reverse = order == "desc"
    if sort == "priority":
        key = lambda insight: (
            _review_priority_score(insight),
            insight.evidence_count,
            insight.severity,
            insight.confidence_score,
            insight.id or 0,
        )
    elif sort == "evidence":
        key = lambda insight: (
            insight.evidence_count,
            insight.severity,
            insight.confidence_score,
            insight.id or 0,
        )
    elif sort == "severity":
        key = lambda insight: (
            insight.severity,
            insight.evidence_count,
            insight.confidence_score,
            insight.id or 0,
        )
    elif sort == "confidence":
        key = lambda insight: (
            insight.confidence_score,
            insight.evidence_count,
            insight.severity,
            insight.id or 0,
        )
    else:
        key = lambda insight: insight.id or 0
    return sorted(insights, key=key, reverse=reverse)


def _route_report_response(report: RouteReport) -> dict:
    geometry = None
    if report.geometry:
        lng, lat = report.geometry["coordinates"]
        geometry = {"lng": lng, "lat": lat}
    return {
        "id": report.id,
        "road_id": report.road_id,
        "report_type": report.report_type,
        "severity": report.severity,
        "message": report.message,
        "geometry": geometry,
        "reported_by": report.reported_by,
        "validation_status": report.validation_status,
        "reviewed_by": report.reviewed_by,
        "reviewed_at": report.reviewed_at,
        "extra_metadata": report.metadata,
        "reported_at": report.reported_at,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def _representative_point(geometry: dict | None) -> dict | None:
    if not geometry:
        return None
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point" and coordinates:
        return {"type": "Point", "coordinates": coordinates}
    if geometry_type == "LineString" and coordinates:
        midpoint = coordinates[len(coordinates) // 2]
        return {"type": "Point", "coordinates": midpoint}
    return None


@router.post(
    "/journeys/start",
    response_model=JourneyReadSchema,
    status_code=201,
    include_in_schema=False,
)
@router.post("/map-traces/start", response_model=JourneyReadSchema, status_code=201)
async def start_journey(
    payload: JourneyStartSchema,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    journey = await service.start_journey(
        Journey(
            user_id=current_user.id,
            profile=payload.profile,
            start_location=payload.start.model_dump(),
            end_location=payload.end.model_dump(),
            planned_distance_m=payload.planned_distance_m,
            planned_duration_s=payload.planned_duration_s,
            planned_route_geometry=payload.planned_route_geometry,
        )
    )
    return _journey_response(journey)


@router.post(
    "/journeys/{trace_id}/positions",
    response_model=list[JourneyPositionReadSchema],
    status_code=201,
    include_in_schema=False,
)
@router.post(
    "/map-traces/{trace_id}/positions",
    response_model=list[JourneyPositionReadSchema],
    status_code=201,
)
async def add_journey_positions(
    trace_id: int,
    payload: JourneyPositionsBatchSchema,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> list[JourneyPositionReadSchema]:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        positions = await service.add_positions(
            journey_id=trace_id,
            user_id=current_user.id,
            positions=[
                JourneyPosition(
                    journey_id=trace_id,
                    location={"lat": item.lat, "lng": item.lng},
                    accuracy_m=item.accuracy_m,
                    speed_mps=item.speed_mps,
                    recorded_at=item.recorded_at,
                )
                for item in payload.positions
            ],
        )
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JourneyNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return [_position_response(position) for position in positions]


@router.post(
    "/journeys/{trace_id}/finish",
    response_model=JourneyReadSchema,
    include_in_schema=False,
)
@router.post("/map-traces/{trace_id}/finish", response_model=JourneyReadSchema)
async def finish_journey(
    trace_id: int,
    payload: JourneyFinishSchema | None = None,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        journey = await service.finish_journey(
            journey_id=trace_id,
            user_id=current_user.id,
            finished_at=(payload or JourneyFinishSchema()).finished_at,
        )
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JourneyNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _journey_response(journey)


@router.get(
    "/journeys/{trace_id}",
    response_model=JourneyDetailReadSchema,
    include_in_schema=False,
)
@router.get("/map-traces/{trace_id}", response_model=JourneyDetailReadSchema)
async def get_journey(
    trace_id: int,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyDetailReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        detail = await service.get_journey(journey_id=trace_id, user_id=current_user.id)
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _detail_response(detail)


@router.post(
    "/journeys/{trace_id}/analyze",
    response_model=JourneyAnalysisReadSchema,
    include_in_schema=False,
)
@router.post("/map-traces/{trace_id}/analyze", response_model=JourneyAnalysisReadSchema)
async def analyze_journey(
    trace_id: int,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyAnalysisReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        analysis = await service.analyze_journey(journey_id=trace_id, user_id=current_user.id)
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JourneyNotFinishedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _analysis_response(analysis)


@router.get(
    "/journeys/{trace_id}/analysis",
    response_model=JourneyAnalysisReadSchema,
    include_in_schema=False,
)
@router.get("/map-traces/{trace_id}/analysis", response_model=JourneyAnalysisReadSchema)
async def get_journey_analysis(
    trace_id: int,
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> JourneyAnalysisReadSchema:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        analysis = await service.get_analysis(journey_id=trace_id, user_id=current_user.id)
    except JourneyAnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _analysis_response(analysis)


@router.get("/journeys", response_model=list[JourneyReadSchema], include_in_schema=False)
@router.get("/map-traces", response_model=list[JourneyReadSchema])
async def list_journeys(
    current_user: User = Depends(get_current_user),
    service: JourneyService = Depends(get_journey_service),
) -> list[JourneyReadSchema]:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return [
        _journey_response(journey)
        for journey in await service.list_journeys(user_id=current_user.id)
    ]


@router.get("/map-trace-insights", response_model=list[MapTraceInsightReadSchema])
async def list_map_trace_insights(
    status: str | None = None,
    insight_type: str | None = None,
    severity_min: int | None = None,
    trace_id: int | None = None,
    sort: str = "newest",
    order: str = "desc",
    _: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> list[MapTraceInsightReadSchema]:
    try:
        insights = await service.list_insights(
            status=status,
            insight_type=insight_type,
            severity_min=severity_min,
            trace_id=trace_id,
        )
    except InvalidMapTraceInsightStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [
        _insight_response(insight)
        for insight in _sort_insights(insights, sort=sort, order=order)
    ]


@router.get(
    "/map-trace-insights/review-queue",
    response_model=list[MapTraceInsightReviewQueueItemSchema],
)
async def list_map_trace_insight_review_queue(
    status: str | None = "proposed",
    insight_type: str | None = None,
    severity_min: int | None = None,
    trace_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> list[MapTraceInsightReviewQueueItemSchema]:
    try:
        insights = await service.list_insights(
            status=status,
            insight_type=insight_type,
            severity_min=severity_min,
            trace_id=trace_id,
        )
    except InvalidMapTraceInsightStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ordered = _sort_insights(insights, sort="priority", order="desc")[:limit]
    return [_insight_review_queue_response(insight) for insight in ordered]


@router.get(
    "/map-trace-insights/route-report-candidates",
    response_model=list[MapTraceInsightReviewQueueItemSchema],
)
async def list_map_trace_route_report_candidates(
    min_evidence_count: int = Query(default=2, ge=1, le=20),
    min_confidence_score: float = Query(default=0.6, ge=0, le=1),
    min_severity: int = Query(default=3, ge=1, le=5),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> list[MapTraceInsightReviewQueueItemSchema]:
    try:
        insights = await service.list_insights(status="validated")
    except InvalidMapTraceInsightStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    candidates = [
        insight
        for insight in insights
        if _conversion_ready(
            insight,
            min_evidence_count=min_evidence_count,
            min_confidence_score=min_confidence_score,
            min_severity=min_severity,
        )
    ]
    ordered = _sort_insights(candidates, sort="priority", order="desc")[:limit]
    return [_insight_review_queue_response(insight) for insight in ordered]


@router.get("/map-trace-insights/{insight_id}", response_model=MapTraceInsightReadSchema)
async def get_map_trace_insight(
    insight_id: int,
    _: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> MapTraceInsightReadSchema:
    try:
        insight = await service.get_insight(insight_id=insight_id)
    except MapTraceInsightNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _insight_response(insight)


@router.get(
    "/map-trace-insights/{insight_id}/detail",
    response_model=MapTraceInsightDetailReadSchema,
)
async def get_map_trace_insight_detail(
    insight_id: int,
    _: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> MapTraceInsightDetailReadSchema:
    try:
        insight = await service.get_insight(insight_id=insight_id)
        detail = await service.get_trace_detail_for_admin(trace_id=insight.journey_id)
    except MapTraceInsightNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        analysis = await service.get_analysis(
            journey_id=insight.journey_id,
            user_id=detail.journey.user_id,
        )
    except JourneyAnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MapTraceInsightDetailReadSchema(
        **_insight_response(insight).model_dump(),
        trace=_detail_response(detail),
        analysis=_analysis_response(analysis),
    )


@router.post(
    "/map-trace-insights/{insight_id}/validate",
    response_model=MapTraceInsightReadSchema,
)
async def validate_map_trace_insight(
    insight_id: int,
    payload: MapTraceInsightReviewSchema | None = None,
    admin: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> MapTraceInsightReadSchema:
    if admin.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        insight = await service.review_insight(
            insight_id=insight_id,
            status="validated",
            reviewed_by=admin.id,
            review_note=(payload or MapTraceInsightReviewSchema()).note,
        )
    except MapTraceInsightNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _insight_response(insight)


@router.post(
    "/map-trace-insights/{insight_id}/reject",
    response_model=MapTraceInsightReadSchema,
)
async def reject_map_trace_insight(
    insight_id: int,
    payload: MapTraceInsightReviewSchema | None = None,
    admin: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> MapTraceInsightReadSchema:
    if admin.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        insight = await service.review_insight(
            insight_id=insight_id,
            status="rejected",
            reviewed_by=admin.id,
            review_note=(payload or MapTraceInsightReviewSchema()).note,
        )
    except MapTraceInsightNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _insight_response(insight)


@router.post(
    "/map-trace-insights/{insight_id}/convert-to-route-report",
    response_model=MapTraceInsightConversionReadSchema,
)
async def convert_map_trace_insight_to_route_report(
    insight_id: int,
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(require_admin),
    service: JourneyService = Depends(get_journey_service),
) -> MapTraceInsightConversionReadSchema:
    try:
        insight = await service.get_insight(insight_id=insight_id)
    except MapTraceInsightNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if insight.status != "validated":
        raise HTTPException(
            status_code=409,
            detail="Only validated map trace insights can be converted",
        )

    report_type = CONVERTIBLE_INSIGHT_REPORT_TYPES.get(insight.insight_type)
    if report_type is None:
        raise HTTPException(
            status_code=422,
            detail=f"Insight type is not convertible: {insight.insight_type}",
        )

    report = RouteReport(
        road_id=None,
        report_type=report_type,
        severity=insight.severity,
        message=f"Observation GPS validee: {insight.message}",
        geometry=_representative_point(insight.geometry),
        reported_by=admin.email,
        metadata={
            "source": "map_trace_insight",
            "source_insight_id": insight.id,
            "source_trace_id": insight.journey_id,
            "source_analysis_id": insight.analysis_id,
            "source_insight_type": insight.insight_type,
            "confidence_score": insight.confidence_score,
            "evidence_count": insight.evidence_count,
            "latest_evidence_trace_id": insight.latest_evidence_trace_id,
        },
    )
    created = await _route_report_workflow(session).propose(report)
    return MapTraceInsightConversionReadSchema(
        insight=_insight_response(insight),
        route_report=_route_report_response(created),
    )
