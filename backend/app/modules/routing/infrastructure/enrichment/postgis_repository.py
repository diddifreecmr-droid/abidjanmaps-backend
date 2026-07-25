from __future__ import annotations

import json

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.routing.application.ports.route_enrichment_repository import RouteEnrichmentRepository
from app.modules.routing.application.services.route_enrichment_models import EnrichmentReport, EnrichmentTroncon, RouteEnrichmentDetail
from app.modules.routing.application.services.route_scoring import RouteLocalFactors
from app.modules.map_data.infrastructure.persistence.models import RoadORM
from app.modules.local_enrichment.infrastructure.persistence.models import RouteReportORM
from app.shared.configuration.settings import settings
from app.shared.domain.vehicle import VehicleContext, build_vehicle_context


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _meters_to_degrees(distance_m: float) -> float:
    # Around Abidjan, one latitude degree is approximately 111.32 km.
    return distance_m / 111_320.0


class SQLAlchemyRouteEnrichmentRepository(RouteEnrichmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build_factors_from_route_geometry(
        self,
        route_geometry: dict,
        vehicle: VehicleContext | None = None,
    ) -> RouteLocalFactors:
        detail = await self.build_detail_from_route_geometry(route_geometry, vehicle)
        return detail.factors

    async def build_detail_from_route_geometry(
        self,
        route_geometry: dict,
        vehicle: VehicleContext | None = None,
    ) -> RouteEnrichmentDetail:
        vehicle = vehicle or build_vehicle_context("car")
        route_geom = func.ST_GeomFromGeoJSON(route_geometry if isinstance(route_geometry, str) else json.dumps(route_geometry))
        match_tolerance = _meters_to_degrees(settings.enrichment_match_tolerance_m)

        roads_result = await self.session.execute(
            select(RoadORM).where(
                RoadORM.validation_status == "validated",
                func.ST_DWithin(RoadORM.geom, route_geom, match_tolerance),
            )
        )
        roads = list(roads_result.scalars().all())
        road_ids = [road.id for road in roads]

        reports_by_id: dict[int, RouteReportORM] = {}
        if road_ids:
            reports_result = await self.session.execute(
                select(RouteReportORM).where(
                    RouteReportORM.validation_status == "validated",
                    RouteReportORM.road_id.in_(road_ids),
                )
            )
            reports_by_id.update(
                (report.id, report) for report in reports_result.scalars().all()
            )

        geo_reports_result = await self.session.execute(
            select(RouteReportORM).where(
                RouteReportORM.validation_status == "validated",
                RouteReportORM.geometry.is_not(None),
                func.ST_DWithin(
                    RouteReportORM.geometry,
                    route_geom,
                    match_tolerance,
                ),
            )
        )
        reports_by_id.update(
            (report.id, report) for report in geo_reports_result.scalars().all()
        )
        reports = list(reports_by_id.values())

        blocked = any(road.is_blocked for road in roads) or any(
            _normalize(report.report_type) in {"blocked", "road_blocked"}
            for report in reports
        )
        degraded = any(
            _normalize(road.surface_state) in {"degraded", "bad", "damaged", "poor"} for road in roads
        ) or any(_normalize(report.report_type) in {"degraded", "damage", "rough"} for report in reports)
        flood_risk = any(
            _normalize(road.seasonal_practicability) in {"flood_risk", "inondable", "rainy_season", "wet"} for road in roads
        ) or any(_normalize(report.report_type) in {"flood", "inondation", "flood_risk"} for report in reports)
        control_point = any(
            _normalize(road.point_controle) not in {"", "none"} for road in roads
        ) or any(
            _normalize(report.report_type) in {"control_point", "checkpoint", "checkpoint_delay"} for report in reports
        )
        unsafe_night = any(
            road.securite_nuit is not None and road.securite_nuit <= 2
            for road in roads
        ) or any(
            _normalize(report.report_type) in {"unsafe_night", "night_risk", "security_night"} for report in reports
        )
        vehicle_forbidden = any(
            vehicle.profile not in (road.allowed_vehicle_profiles or [])
            for road in roads
        )
        vehicle_overweight = any(
            road.tonnage_max_reel_t is not None
            and vehicle.weight_t > road.tonnage_max_reel_t
            for road in roads
        )
        vehicle_too_wide = any(
            road.width_usable_m is not None
            and vehicle.width_m + 0.5 > road.width_usable_m
            for road in roads
        )
        narrow_width = any(
            road.width_usable_m is not None
            and road.width_usable_m < vehicle.recommended_road_width_m
            for road in roads
        )
        toll_present = any(_normalize(road.type_flux) in {"toll", "peage"} for road in roads) or any(
            _normalize(report.report_type) in {"toll", "peage"} for report in reports
        )

        flood_count = sum(1 for road in roads if _normalize(road.seasonal_practicability) in {"flood_risk", "inondable", "rainy_season", "wet"})
        degraded_count = sum(1 for road in roads if _normalize(road.surface_state) in {"degraded", "bad", "damaged", "poor"})
        report_severity = sum(report.severity for report in reports)

        seasonal_risk_multiplier = 1.0 + min(0.35, 0.12 * flood_count + 0.03 * report_severity)
        surface_sensitivity = {
            "motorcycle": 0.12,
            "car": 0.10,
            "truck": 0.06,
        }[vehicle.profile]
        vehicle_profile_multiplier = 1.0 + min(
            0.30,
            surface_sensitivity * degraded_count,
        )

        factors = RouteLocalFactors(
            blocked=blocked,
            degraded=degraded,
            flood_risk=flood_risk,
            control_point=control_point,
            unsafe_night=unsafe_night,
            narrow_width=narrow_width,
            toll_present=toll_present,
            requested_vehicle_profile=vehicle.profile,
            vehicle_width_m=vehicle.width_m,
            vehicle_weight_t=vehicle.weight_t,
            vehicle_forbidden=vehicle_forbidden,
            vehicle_overweight=vehicle_overweight,
            vehicle_too_wide=vehicle_too_wide,
            seasonal_risk_multiplier=round(seasonal_risk_multiplier, 2),
            vehicle_profile_multiplier=round(vehicle_profile_multiplier, 2),
        )
        troncons = [
            EnrichmentTroncon(
                road_id=road.id,
                road_name=road.name,
                validation_status=road.validation_status,
                surface_state=road.surface_state,
                seasonal_practicability=road.seasonal_practicability,
                is_blocked=road.is_blocked,
                point_controle=road.point_controle,
                width_usable_m=road.width_usable_m,
                tonnage_max_reel_t=road.tonnage_max_reel_t,
                allowed_vehicle_profiles=road.allowed_vehicle_profiles,
                securite_nuit=road.securite_nuit,
                type_flux=road.type_flux,
            )
            for road in roads
        ]
        detail_reports = [
            EnrichmentReport(
                id=report.id,
                road_id=report.road_id,
                report_type=report.report_type,
                severity=report.severity,
                message=report.message,
            )
            for report in reports
        ]
        return RouteEnrichmentDetail(factors=factors, troncons=troncons, reports=detail_reports)
