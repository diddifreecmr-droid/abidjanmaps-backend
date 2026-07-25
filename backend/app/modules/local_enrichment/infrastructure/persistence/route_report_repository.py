from dataclasses import replace
from datetime import datetime, timezone

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.local_enrichment.application.ports.route_report_repository import RouteReportRepository
from app.modules.local_enrichment.domain.entities.route_report import RouteReport
from app.modules.local_enrichment.infrastructure.persistence.mappers import (
    point_to_wkt,
    route_report_from_orm,
    route_report_to_orm,
)
from app.modules.local_enrichment.infrastructure.persistence.models import (
    RouteReportHistoryORM,
    RouteReportORM,
)


class SQLAlchemyRouteReportRepository(RouteReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, report: RouteReport) -> RouteReport:
        orm = route_report_to_orm(report)
        self.session.add(orm)
        await self.session.flush()
        self.session.add(
            RouteReportHistoryORM(
                route_report_id=orm.id,
                action="propose",
                new_value={"validation_status": "proposed"},
                changed_by=report.reported_by,
                note="Route report proposed",
            )
        )
        await self.session.commit()
        await self.session.refresh(orm)
        created = route_report_from_orm(orm)
        return replace(created, geometry=report.geometry)

    async def list_all(self, validation_status: str | None = None) -> list[RouteReport]:
        statement = select(RouteReportORM)
        if validation_status is not None:
            statement = statement.where(RouteReportORM.validation_status == validation_status)
        result = await self.session.execute(statement.order_by(RouteReportORM.id.desc()))
        return [route_report_from_orm(item) for item in result.scalars().all()]

    async def get_by_id(self, report_id: int) -> RouteReport | None:
        result = await self.session.execute(select(RouteReportORM).where(RouteReportORM.id == report_id))
        report = result.scalar_one_or_none()
        return route_report_from_orm(report) if report is not None else None

    async def update(
        self,
        report_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> RouteReport | None:
        result = await self.session.execute(
            select(RouteReportORM).where(RouteReportORM.id == report_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            return None

        field_mapping = {
            "road_id": "road_id",
            "report_type": "report_type",
            "severity": "severity",
            "message": "message",
            "geometry": "geometry",
            "extra_metadata": "extra_metadata",
            "validation_status": "validation_status",
            "reviewed_by": "reviewed_by",
            "reviewed_at": "reviewed_at",
        }
        old_values: dict = {}
        new_values: dict = {}

        for field_name, value in changes.items():
            orm_field = field_mapping.get(field_name)
            if orm_field is None:
                continue
            if field_name == "geometry":
                old_geometry = await self.session.scalar(
                    select(func.ST_AsGeoJSON(RouteReportORM.geometry)).where(
                        RouteReportORM.id == report_id
                    )
                )
                old_values[field_name] = json.loads(old_geometry) if old_geometry else None
                setattr(report, orm_field, point_to_wkt(value) if value else None)
            else:
                old_value = getattr(report, orm_field)
                old_values[field_name] = (
                    old_value.isoformat()
                    if isinstance(old_value, datetime)
                    else old_value
                )
                setattr(report, orm_field, value)
            new_values[field_name] = value

        await self.session.flush()
        self.session.add(
            RouteReportHistoryORM(
                route_report_id=report_id,
                action="update",
                old_value=old_values,
                new_value=new_values,
                changed_by=changed_by,
                note=note,
            )
        )
        await self.session.commit()
        await self.session.refresh(report)
        return route_report_from_orm(report)

    async def set_validation_status(
        self,
        report_id: int,
        status: str,
        reviewed_by: str | None = None,
        note: str | None = None,
    ) -> RouteReport | None:
        result = await self.session.execute(
            select(RouteReportORM).where(RouteReportORM.id == report_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            return None

        old_status = report.validation_status
        report.validation_status = status
        report.reviewed_by = reviewed_by
        report.reviewed_at = datetime.now(timezone.utc)
        self.session.add(
            RouteReportHistoryORM(
                route_report_id=report_id,
                action="validate" if status == "validated" else "reject",
                old_value={"validation_status": old_status},
                new_value={"validation_status": status},
                changed_by=reviewed_by,
                note=note,
            )
        )
        await self.session.commit()
        await self.session.refresh(report)
        return route_report_from_orm(report)

    async def list_history(self, report_id: int) -> list[RouteReportHistoryORM]:
        result = await self.session.execute(
            select(RouteReportHistoryORM)
            .where(RouteReportHistoryORM.route_report_id == report_id)
            .order_by(RouteReportHistoryORM.id.desc())
        )
        return list(result.scalars().all())
