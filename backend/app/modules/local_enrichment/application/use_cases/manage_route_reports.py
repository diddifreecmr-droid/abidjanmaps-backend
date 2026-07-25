from app.modules.local_enrichment.application.ports.road_history_writer import RoadHistoryWriter
from app.modules.local_enrichment.application.ports.route_report_repository import (
    RouteReportRepository,
)
from app.modules.local_enrichment.domain.entities.route_report import RouteReport


class RouteReportWorkflow:
    def __init__(
        self,
        repository: RouteReportRepository,
        road_history: RoadHistoryWriter,
    ) -> None:
        self.repository = repository
        self.road_history = road_history

    async def propose(self, report: RouteReport) -> RouteReport:
        proposed = RouteReport(
            road_id=report.road_id,
            report_type=report.report_type,
            severity=report.severity,
            message=report.message,
            geometry=report.geometry,
            reported_by=report.reported_by,
            validation_status="proposed",
            metadata=report.metadata,
            reported_at=report.reported_at,
        )
        created = await self.repository.create(proposed)
        if created.road_id is not None:
            await self.road_history.add_history_entry(
                road_id=created.road_id,
                action="route_report_proposed",
                field_name="route_reports",
                new_value={
                    "report_id": created.id,
                    "report_type": created.report_type,
                    "severity": created.severity,
                    "validation_status": created.validation_status,
                },
                changed_by=created.reported_by,
                note="Local route report proposed",
            )
        return created

    async def review(
        self,
        report_id: int,
        status: str,
        reviewed_by: str | None = None,
        note: str | None = None,
    ) -> RouteReport | None:
        if status not in {"validated", "rejected"}:
            raise ValueError(f"Unsupported review decision: {status}")

        existing = await self.repository.get_by_id(report_id)
        if existing is None:
            return None

        updated = await self.repository.set_validation_status(
            report_id=report_id,
            status=status,
            reviewed_by=reviewed_by,
            note=note,
        )
        if updated is not None and updated.road_id is not None:
            await self.road_history.add_history_entry(
                road_id=updated.road_id,
                action=f"route_report_{status}",
                field_name="route_reports.validation_status",
                old_value={
                    "report_id": report_id,
                    "validation_status": existing.validation_status,
                },
                new_value={
                    "report_id": report_id,
                    "validation_status": status,
                },
                changed_by=reviewed_by,
                note=note,
            )
        return updated

    async def update(
        self,
        report_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> RouteReport | None:
        existing = await self.repository.get_by_id(report_id)
        if existing is None:
            return None

        unpublished_changes = {
            **changes,
            "validation_status": "proposed",
            "reviewed_by": None,
            "reviewed_at": None,
        }
        updated = await self.repository.update(
            report_id=report_id,
            changes=unpublished_changes,
            changed_by=changed_by,
            note=note,
        )
        if updated is None:
            return None

        affected_road_ids = {
            road_id
            for road_id in (existing.road_id, updated.road_id)
            if road_id is not None
        }
        for road_id in affected_road_ids:
            await self.road_history.add_history_entry(
                road_id=road_id,
                action="route_report_updated",
                field_name="route_reports",
                old_value={
                    "report_id": report_id,
                    "road_id": existing.road_id,
                    "validation_status": existing.validation_status,
                },
                new_value={
                    "report_id": report_id,
                    "road_id": updated.road_id,
                    "validation_status": updated.validation_status,
                },
                changed_by=changed_by,
                note=note,
            )
        return updated
