from app.modules.routing.application.dto import RouteRequestDTO
from app.modules.routing.application.ports.routing_engine import RoutingEngine
from app.modules.routing.domain.entities.coordinate import Coordinate
from app.modules.routing.domain.entities.price import Price
from app.modules.routing.domain.entities.route import Route
from app.shared.domain.exceptions import InvalidProfileError
from app.shared.domain.exceptions import OutOfCoverageError
from app.modules.routing.domain.services.coverage import CoverageService
from app.modules.routing.domain.services.pricing import PricingService
from app.shared.domain.vehicle import VEHICLE_PROFILES


class CalculateRoute:
    def __init__(
        self,
        routing_engine: RoutingEngine,
        pricing_service: PricingService,
        coverage_service: CoverageService,
    ) -> None:
        self.routing_engine = routing_engine
        self.pricing_service = pricing_service
        self.coverage_service = coverage_service

    def execute(self, request: RouteRequestDTO, request_id: str | None = None) -> tuple[Route, Price]:
        if request.profile not in VEHICLE_PROFILES:
            raise InvalidProfileError("Unsupported profile")
        start = Coordinate(lat=request.start_lat, lng=request.start_lng)
        end = Coordinate(lat=request.end_lat, lng=request.end_lng)
        if not self.coverage_service.is_covered(start) or not self.coverage_service.is_covered(end):
            raise OutOfCoverageError("Out of coverage")
        route = self.routing_engine.calculate_route(start, end, request.profile, request_id=request_id)
        price = self.pricing_service.calculate_price(route.distance_m, route.duration_s, request.profile)
        return route, price

    def execute_with_alternatives(
        self,
        request: RouteRequestDTO,
        request_id: str | None = None,
        max_alternatives: int = 3,
    ) -> list[tuple[Route, Price]]:
        if request.profile not in VEHICLE_PROFILES:
            raise InvalidProfileError("Unsupported profile")
        start = Coordinate(lat=request.start_lat, lng=request.start_lng)
        end = Coordinate(lat=request.end_lat, lng=request.end_lng)
        if not self.coverage_service.is_covered(start) or not self.coverage_service.is_covered(end):
            raise OutOfCoverageError("Out of coverage")

        routes = self.routing_engine.calculate_routes(start, end, request_id=request_id, max_alternatives=max_alternatives)
        return [
            (
                route,
                self.pricing_service.calculate_price(route.distance_m, route.duration_s, request.profile),
            )
            for route in routes
        ]
