from fastapi.testclient import TestClient

from app.modules.routing.application.dto import RouteRequestDTO
from app.modules.routing.application.use_cases.calculate_route import CalculateRoute
from app.modules.routing.domain.entities.coordinate import Coordinate
from app.modules.routing.domain.entities.price import Price
from app.modules.routing.domain.entities.route import Route
from app.main import app
from app.modules.routing.presentation.route_api import get_calculate_route_use_case
from app.modules.routing.presentation.schemas import RouteRequestSchema


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_route_validation_returns_400_for_invalid_profile() -> None:
    response = client.post(
        "/api/v1/route",
        json={
            "start": {"lat": 5.3364, "lng": -4.0267},
            "end": {"lat": 5.3097, "lng": -3.9903},
            "profile": "bicycle",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_french_motorcycle_alias_is_normalized() -> None:
    payload = RouteRequestSchema(
        start={"lat": 5.3364, "lng": -4.0267},
        end={"lat": 5.3097, "lng": -3.9903},
        profile="moto",
    )
    assert payload.profile == "motorcycle"
    assert payload.vehicle_width_m is None
    assert payload.vehicle_weight_t is None


class FakeRoutingEngine:
    def calculate_route(self, start: Coordinate, end: Coordinate, profile: str, request_id: str | None = None) -> Route:
        return Route(
            geometry={"type": "LineString", "coordinates": [[-4.02003, 5.3329], [-3.97754, 5.33892]]},
            distance_m=1450,
            duration_s=360,
        )


class FakePricingService:
    def calculate_price(self, distance_m: int, duration_s: int, profile: str) -> Price:
        return Price(amount=1100)


class FakeCoverageService:
    def is_covered(self, coordinate: Coordinate) -> bool:
        return True


def test_route_success_with_fake_use_case() -> None:
    def override_use_case() -> CalculateRoute:
        return CalculateRoute(
            routing_engine=FakeRoutingEngine(),
            pricing_service=FakePricingService(),
            coverage_service=FakeCoverageService(),
        )

    app.dependency_overrides[get_calculate_route_use_case] = override_use_case
    try:
        response = client.post(
            "/api/v1/route",
            json={
                "start": {"lat": 5.3329, "lng": -4.02003},
                "end": {"lat": 5.33892, "lng": -3.97754},
                "profile": "car",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["route"]["distance_m"] == 1450
    assert body["price"]["amount"] == 1100
