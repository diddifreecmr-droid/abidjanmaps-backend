from geoalchemy2.elements import WKTElement

from app.modules.local_enrichment.domain.taxonomy import normalize_route_report_type
from app.modules.local_enrichment.domain.entities.route_report import RouteReport
from app.modules.local_enrichment.infrastructure.persistence.models import RouteReportORM


def point_to_wkt(geometry: dict) -> WKTElement:
    lng, lat = geometry["coordinates"]
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def route_report_to_orm(report: RouteReport) -> RouteReportORM:
    return RouteReportORM(
        road_id=report.road_id,
        report_type=normalize_route_report_type(report.report_type),
        severity=report.severity,
        message=report.message,
        geometry=point_to_wkt(report.geometry) if report.geometry else None,
        reported_by=report.reported_by,
        validation_status=report.validation_status,
        reviewed_by=report.reviewed_by,
        reviewed_at=report.reviewed_at,
        extra_metadata=report.metadata,
        reported_at=report.reported_at,
    )


def route_report_from_orm(report: RouteReportORM) -> RouteReport:
    return RouteReport(
        id=report.id,
        road_id=report.road_id,
        report_type=report.report_type,
        severity=report.severity,
        message=report.message,
        reported_by=report.reported_by,
        validation_status=report.validation_status,
        reviewed_by=report.reviewed_by,
        reviewed_at=report.reviewed_at,
        metadata=report.extra_metadata,
        reported_at=report.reported_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )
