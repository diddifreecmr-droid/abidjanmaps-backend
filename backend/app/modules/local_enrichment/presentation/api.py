from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.local_enrichment.application.use_cases.manage_route_reports import (
    RouteReportWorkflow,
)
from app.modules.local_enrichment.domain.entities.route_report import RouteReport
from app.modules.local_enrichment.domain.taxonomy import route_report_taxonomy_documentation
from app.modules.local_enrichment.infrastructure.persistence.route_report_repository import SQLAlchemyRouteReportRepository
from app.modules.local_enrichment.presentation.schemas import (
    RouteReportCreateSchema,
    RouteReportPatchSchema,
    RouteReportReadSchema,
    RouteReportReviewSchema,
)
from app.modules.map_data.infrastructure.persistence.road_repository import SQLAlchemyRoadRepository
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user, require_admin
from app.shared.infrastructure.db import get_async_session

router = APIRouter(tags=["route-reports"])


@router.get("/route-reports/taxonomy")
async def route_reports_taxonomy() -> dict:
    return route_report_taxonomy_documentation()


def _point_to_geojson(schema) -> dict:
    return {"type": "Point", "coordinates": [schema.lng, schema.lat]}


def _report_response(report: RouteReport) -> dict:
    return {
        "id": report.id,
        "road_id": report.road_id,
        "report_type": report.report_type,
        "severity": report.severity,
        "message": report.message,
        "reported_by": report.reported_by,
        "validation_status": report.validation_status,
        "reviewed_by": report.reviewed_by,
        "reviewed_at": report.reviewed_at,
        "extra_metadata": report.metadata,
        "reported_at": report.reported_at,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def _workflow(session: AsyncSession) -> RouteReportWorkflow:
    return RouteReportWorkflow(
        repository=SQLAlchemyRouteReportRepository(session),
        road_history=SQLAlchemyRoadRepository(session),
    )


@router.post("/route-reports", response_model=RouteReportReadSchema, status_code=201)
async def create_route_report(
    payload: RouteReportCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> RouteReportReadSchema:
    report = RouteReport(
        road_id=payload.road_id,
        report_type=payload.report_type,
        severity=payload.severity,
        message=payload.message,
        geometry=_point_to_geojson(payload.geometry) if payload.geometry else None,
        reported_by=current_user.email,
        metadata=payload.extra_metadata,
    )
    created = await _workflow(session).propose(report)
    return RouteReportReadSchema(
        **_report_response(created),
        geometry=payload.geometry,
    )


@router.get("/route-reports")
async def list_route_reports(
    status: str | None = Query(
        default=None,
        pattern="^(proposed|validated|rejected)$",
    ),
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    repo = SQLAlchemyRouteReportRepository(session)
    reports = await repo.list_all(validation_status=status)
    return [_report_response(report) for report in reports]


@router.get("/route-reports/{report_id}")
async def get_route_report(report_id: int, session: AsyncSession = Depends(get_async_session)) -> dict:
    repo = SQLAlchemyRouteReportRepository(session)
    report = await repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Route report not found")
    return _report_response(report)


@router.patch("/route-reports/{report_id}")
async def update_route_report(
    report_id: int,
    payload: RouteReportPatchSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    changes = payload.model_dump(
        exclude_unset=True,
        exclude={"note"},
    )
    if "geometry" in payload.model_fields_set:
        changes["geometry"] = (
            _point_to_geojson(payload.geometry)
            if payload.geometry is not None
            else None
        )
    report = await _workflow(session).update(
        report_id=report_id,
        changes=changes,
        changed_by=current_user.email,
        note=payload.note,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Route report not found")
    return _report_response(report)


@router.post("/route-reports/{report_id}/validate")
async def validate_route_report(
    report_id: int,
    payload: RouteReportReviewSchema | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
) -> dict:
    review = payload or RouteReportReviewSchema()
    report = await _workflow(session).review(
        report_id=report_id,
        status="validated",
        reviewed_by=current_user.email,
        note=review.note,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Route report not found")
    return _report_response(report)


@router.post("/route-reports/{report_id}/reject")
async def reject_route_report(
    report_id: int,
    payload: RouteReportReviewSchema | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
) -> dict:
    review = payload or RouteReportReviewSchema()
    report = await _workflow(session).review(
        report_id=report_id,
        status="rejected",
        reviewed_by=current_user.email,
        note=review.note,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Route report not found")
    return _report_response(report)


@router.get("/route-reports/{report_id}/history")
async def route_report_history(
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    repo = SQLAlchemyRouteReportRepository(session)
    if await repo.get_by_id(report_id) is None:
        raise HTTPException(status_code=404, detail="Route report not found")
    items = await repo.list_history(report_id)
    return [
        {
            "id": item.id,
            "route_report_id": item.route_report_id,
            "action": item.action,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "changed_by": item.changed_by,
            "note": item.note,
            "created_at": item.created_at,
        }
        for item in items
    ]
