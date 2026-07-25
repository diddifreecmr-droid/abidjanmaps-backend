from app.modules.routing.application.dto import RouteRequestDTO
from app.modules.routing.application.use_cases.calculate_route import CalculateRoute
from app.modules.routing.domain.entities.coordinate import Coordinate
from app.modules.routing.domain.entities.price import Price
from app.modules.routing.domain.entities.route import Route
from app.shared.configuration.settings import settings


class FakeRoutingEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[Coordinate, Coordinate, str, str | None]] = []

    def calculate_route(
        self,
        start: Coordinate,
        end: Coordinate,
        profile: str,
        request_id: str | None = None,
    ) -> Route:
        self.calls.append((start, end, profile, request_id))
        return Route(
            geometry={"type": "LineString", "coordinates": [[-4.0, 5.3], [-3.9, 5.4]]},
            distance_m=1200,
            duration_s=300,
        )


class FakePricingService:
    def calculate_price(self, distance_m: int, duration_s: int, profile: str) -> Price:
        return Price(amount=1000)


class FakeCoverageService:
    def is_covered(self, coordinate: Coordinate) -> bool:
        return True


def test_calculate_route_success() -> None:
    engine = FakeRoutingEngine()
    use_case = CalculateRoute(
        routing_engine=engine,
        pricing_service=FakePricingService(),
        coverage_service=FakeCoverageService(),
    )

    request = RouteRequestDTO(
        start_lat=5.3329,
        start_lng=-4.02003,
        end_lat=5.33892,
        end_lng=-3.97754,
        profile=settings.allowed_profile,
    )

    route, price = use_case.execute(request, request_id="test-request")

    assert route.distance_m == 1200
    assert route.duration_s == 300
    assert price.amount == 1000
    assert engine.calls[0][3] == "test-request"
