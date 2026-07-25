from fastapi import APIRouter, Depends, Request

from app.modules.routing.application.dto import RouteRequestDTO
from app.modules.routing.application.use_cases.calculate_route import CalculateRoute
from app.modules.routing.infrastructure.coverage.bounding_box_coverage import BoundingBoxCoverageService
from app.modules.routing.infrastructure.pricing.default_pricing_service import DefaultPricingService
from app.modules.routing.infrastructure.osrm.engine import OSRMRoutingEngine
from app.modules.routing.presentation.schemas import (
    PriceSchema,
    RouteGeometrySchema,
    RouteRequestSchema,
    RouteResponseSchema,
    RouteSchema,
)

router = APIRouter(tags=["routing"])


def get_calculate_route_use_case() -> CalculateRoute:
    return CalculateRoute(
        routing_engine=OSRMRoutingEngine(),
        pricing_service=DefaultPricingService(),
        coverage_service=BoundingBoxCoverageService(),
    )


@router.post("/route", response_model=RouteResponseSchema)
def calculate_route(
    request: Request,
    payload: RouteRequestSchema,
    use_case: CalculateRoute = Depends(get_calculate_route_use_case),
) -> RouteResponseSchema:
    request_dto = RouteRequestDTO(
        start_lat=payload.start.lat,
        start_lng=payload.start.lng,
        end_lat=payload.end.lat,
        end_lng=payload.end.lng,
        profile=payload.profile,
    )
    route, price = use_case.execute(request_dto, request_id=getattr(request.state, "request_id", None))
    return RouteResponseSchema(
        status="ok",
        route=RouteSchema(
            geometry=RouteGeometrySchema(**route.geometry),
            distance_m=route.distance_m,
            duration_s=route.duration_s,
        ),
        price=PriceSchema(amount=price.amount, currency=price.currency),
    )
