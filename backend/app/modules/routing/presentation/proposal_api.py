from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.routing.application.dto import RouteRequestDTO
from app.modules.routing.application.use_cases.calculate_route import CalculateRoute
from app.modules.routing.application.services.route_enrichment import RouteEnrichmentService
from app.modules.routing.application.services.route_enrichment_models import RouteEnrichmentDetail
from app.modules.routing.application.services.route_scoring import RouteScoringService
from app.modules.routing.infrastructure.coverage.bounding_box_coverage import BoundingBoxCoverageService
from app.shared.infrastructure.db import get_async_session
from app.modules.routing.infrastructure.pricing.default_pricing_service import DefaultPricingService
from app.modules.routing.infrastructure.enrichment.postgis_repository import SQLAlchemyRouteEnrichmentRepository
from app.modules.routing.infrastructure.osrm.engine import OSRMRoutingEngine
from app.modules.routing.presentation.schemas import (
    PriceSchema,
    RouteGeometrySchema,
    RouteProposalDetailResponseSchema,
    RouteProposalResponseSchema,
    RouteProposalSchema,
    RouteRequestSchema,
    RouteSchema,
)
from app.shared.domain.vehicle import build_vehicle_context

router = APIRouter(tags=["routing"])


def get_calculate_route_use_case() -> CalculateRoute:
    return CalculateRoute(
        routing_engine=OSRMRoutingEngine(),
        pricing_service=DefaultPricingService(),
        coverage_service=BoundingBoxCoverageService(),
    )


def get_route_enrichment_service(session: AsyncSession = Depends(get_async_session)) -> RouteEnrichmentService:
    return RouteEnrichmentService(SQLAlchemyRouteEnrichmentRepository(session))


@router.post("/routes/proposals", response_model=RouteProposalResponseSchema)
async def calculate_route_proposals(
    request: Request,
    payload: RouteRequestSchema,
    enrichment_service: RouteEnrichmentService = Depends(get_route_enrichment_service),
    use_case: CalculateRoute = Depends(get_calculate_route_use_case),
) -> RouteProposalResponseSchema:
    request_dto = RouteRequestDTO(
        start_lat=payload.start.lat,
        start_lng=payload.start.lng,
        end_lat=payload.end.lat,
        end_lng=payload.end.lng,
        profile=payload.profile,
    )
    proposals = use_case.execute_with_alternatives(
        request_dto,
        request_id=getattr(request.state, "request_id", None),
        max_alternatives=3,
    )
    scoring_service = RouteScoringService()
    vehicle = build_vehicle_context(
        payload.profile,
        width_m=payload.vehicle_width_m,
        weight_t=payload.vehicle_weight_t,
    )
    factors = []
    details = []
    for route, _price in proposals:
        detail = await enrichment_service.build_detail_from_route_geometry(
            route.geometry,
            vehicle,
        )
        details.append(detail)
        factors.append(detail.factors)
    scored = scoring_service.rank_routes([route for route, _ in proposals], factors=factors)
    proposal_map = {id(route): price for route, price in proposals}
    detail_map = {
        id(route): details[index]
        for index, (route, _price) in enumerate(proposals)
    }
    return RouteProposalResponseSchema(
        status="ok",
        proposals=[
            RouteProposalSchema(
                route=RouteSchema(
                    geometry=RouteGeometrySchema(**scored_item.route.geometry),
                    distance_m=scored_item.route.distance_m,
                    duration_s=scored_item.route.duration_s,
                ),
                price=PriceSchema(
                    amount=proposal_map[id(scored_item.route)].amount,
                    currency=proposal_map[id(scored_item.route)].currency,
                ),
                score=scored_item.score,
                rank=scored_item.rank,
                score_breakdown={
                    "base": {
                        "distance_component": scored_item.breakdown.distance_component,
                        "duration_component": scored_item.breakdown.duration_component,
                        "base_score": scored_item.breakdown.base_score,
                    },
                    "penalties": {
                        "blocked": scored_item.breakdown.blocked_penalty,
                        "degraded": scored_item.breakdown.degraded_penalty,
                        "flood": scored_item.breakdown.flood_penalty,
                        "control": scored_item.breakdown.control_penalty,
                        "unsafe_night": scored_item.breakdown.unsafe_night_penalty,
                        "narrow_width": scored_item.breakdown.narrow_width_penalty,
                        "toll": scored_item.breakdown.toll_penalty,
                        "seasonal": scored_item.breakdown.seasonal_penalty,
                        "vehicle": scored_item.breakdown.vehicle_penalty,
                    },
                    "vehicle_constraints": {
                        "profile": detail_map[id(scored_item.route)].factors.requested_vehicle_profile,
                        "width_m": detail_map[id(scored_item.route)].factors.vehicle_width_m,
                        "weight_t": detail_map[id(scored_item.route)].factors.vehicle_weight_t,
                        "forbidden": detail_map[id(scored_item.route)].factors.vehicle_forbidden,
                        "overweight": detail_map[id(scored_item.route)].factors.vehicle_overweight,
                        "too_wide": detail_map[id(scored_item.route)].factors.vehicle_too_wide,
                        "eligible": not any(
                            (
                                detail_map[id(scored_item.route)].factors.vehicle_forbidden,
                                detail_map[id(scored_item.route)].factors.vehicle_overweight,
                                detail_map[id(scored_item.route)].factors.vehicle_too_wide,
                            )
                        ),
                    },
                    "total_score": scored_item.breakdown.total_score,
                },
                enrichment=_detail_to_dict(detail_map[id(scored_item.route)]),
            )
            for scored_item in scored
        ],
    )


@router.post("/routes/proposals/detail", response_model=RouteProposalDetailResponseSchema)
async def calculate_route_proposals_detail(
    request: Request,
    payload: RouteRequestSchema,
    enrichment_service: RouteEnrichmentService = Depends(get_route_enrichment_service),
    use_case: CalculateRoute = Depends(get_calculate_route_use_case),
) -> RouteProposalDetailResponseSchema:
    request_dto = RouteRequestDTO(
        start_lat=payload.start.lat,
        start_lng=payload.start.lng,
        end_lat=payload.end.lat,
        end_lng=payload.end.lng,
        profile=payload.profile,
    )
    proposals = use_case.execute_with_alternatives(
        request_dto,
        request_id=getattr(request.state, "request_id", None),
        max_alternatives=3,
    )
    scoring_service = RouteScoringService()
    vehicle = build_vehicle_context(
        payload.profile,
        width_m=payload.vehicle_width_m,
        weight_t=payload.vehicle_weight_t,
    )
    factors = []
    details = []
    for route, _price in proposals:
        detail = await enrichment_service.build_detail_from_route_geometry(
            route.geometry,
            vehicle,
        )
        details.append(detail)
        factors.append(detail.factors)
    scored = scoring_service.rank_routes([route for route, _ in proposals], factors=factors)
    proposal_map = {id(route): price for route, price in proposals}
    detail_map = {
        id(route): details[index]
        for index, (route, _price) in enumerate(proposals)
    }
    return RouteProposalDetailResponseSchema(
        status="ok",
        proposals=[
            RouteProposalSchema(
                route=RouteSchema(
                    geometry=RouteGeometrySchema(**scored_item.route.geometry),
                    distance_m=scored_item.route.distance_m,
                    duration_s=scored_item.route.duration_s,
                ),
                price=PriceSchema(
                    amount=proposal_map[id(scored_item.route)].amount,
                    currency=proposal_map[id(scored_item.route)].currency,
                ),
                score=scored_item.score,
                rank=scored_item.rank,
                score_breakdown={
                    "base": {
                        "distance_component": scored_item.breakdown.distance_component,
                        "duration_component": scored_item.breakdown.duration_component,
                        "base_score": scored_item.breakdown.base_score,
                    },
                    "penalties": {
                        "blocked": scored_item.breakdown.blocked_penalty,
                        "degraded": scored_item.breakdown.degraded_penalty,
                        "flood": scored_item.breakdown.flood_penalty,
                        "control": scored_item.breakdown.control_penalty,
                        "unsafe_night": scored_item.breakdown.unsafe_night_penalty,
                        "narrow_width": scored_item.breakdown.narrow_width_penalty,
                        "toll": scored_item.breakdown.toll_penalty,
                        "seasonal": scored_item.breakdown.seasonal_penalty,
                        "vehicle": scored_item.breakdown.vehicle_penalty,
                    },
                    "vehicle_constraints": {
                        "profile": detail_map[id(scored_item.route)].factors.requested_vehicle_profile,
                        "width_m": detail_map[id(scored_item.route)].factors.vehicle_width_m,
                        "weight_t": detail_map[id(scored_item.route)].factors.vehicle_weight_t,
                        "forbidden": detail_map[id(scored_item.route)].factors.vehicle_forbidden,
                        "overweight": detail_map[id(scored_item.route)].factors.vehicle_overweight,
                        "too_wide": detail_map[id(scored_item.route)].factors.vehicle_too_wide,
                        "eligible": not any(
                            (
                                detail_map[id(scored_item.route)].factors.vehicle_forbidden,
                                detail_map[id(scored_item.route)].factors.vehicle_overweight,
                                detail_map[id(scored_item.route)].factors.vehicle_too_wide,
                            )
                        ),
                    },
                    "total_score": scored_item.breakdown.total_score,
                },
                enrichment=_detail_to_dict(detail_map[id(scored_item.route)]),
            )
            for scored_item in scored
        ],
    )


def _detail_to_dict(detail: RouteEnrichmentDetail) -> dict:
    return {
        "factors": {
            "blocked": detail.factors.blocked,
            "degraded": detail.factors.degraded,
            "flood_risk": detail.factors.flood_risk,
            "control_point": detail.factors.control_point,
            "unsafe_night": detail.factors.unsafe_night,
            "narrow_width": detail.factors.narrow_width,
            "toll_present": detail.factors.toll_present,
            "requested_vehicle_profile": detail.factors.requested_vehicle_profile,
            "vehicle_width_m": detail.factors.vehicle_width_m,
            "vehicle_weight_t": detail.factors.vehicle_weight_t,
            "vehicle_forbidden": detail.factors.vehicle_forbidden,
            "vehicle_overweight": detail.factors.vehicle_overweight,
            "vehicle_too_wide": detail.factors.vehicle_too_wide,
            "seasonal_risk_multiplier": detail.factors.seasonal_risk_multiplier,
            "vehicle_profile_multiplier": detail.factors.vehicle_profile_multiplier,
        },
        "troncons": [
            {
                "road_id": troncon.road_id,
                "road_name": troncon.road_name,
                "validation_status": troncon.validation_status,
                "surface_state": troncon.surface_state,
                "seasonal_practicability": troncon.seasonal_practicability,
                "is_blocked": troncon.is_blocked,
                "point_controle": troncon.point_controle,
                "width_usable_m": troncon.width_usable_m,
                "tonnage_max_reel_t": troncon.tonnage_max_reel_t,
                "allowed_vehicle_profiles": troncon.allowed_vehicle_profiles,
                "securite_nuit": troncon.securite_nuit,
                "type_flux": troncon.type_flux,
            }
            for troncon in detail.troncons
        ],
        "reports": [
            {
                "id": report.id,
                "road_id": report.road_id,
                "report_type": report.report_type,
                "severity": report.severity,
                "message": report.message,
            }
            for report in detail.reports
        ],
    }
