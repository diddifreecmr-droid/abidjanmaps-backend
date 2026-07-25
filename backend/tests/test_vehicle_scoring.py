from app.modules.routing.application.services.route_scoring import (
    RouteLocalFactors,
    RouteScoringService,
)
from app.modules.routing.domain.entities.route import Route
from app.shared.domain.vehicle import build_vehicle_context


def _route() -> Route:
    return Route(
        geometry={"type": "LineString", "coordinates": [[-4.0, 5.3], [-3.9, 5.4]]},
        distance_m=1_000,
        duration_s=300,
    )


def test_vehicle_profile_defaults_and_aliases() -> None:
    motorcycle = build_vehicle_context("moto")
    truck = build_vehicle_context("camion", width_m=2.8, weight_t=25)

    assert motorcycle.profile == "motorcycle"
    assert motorcycle.weight_t == 0.5
    assert truck.profile == "truck"
    assert truck.width_m == 2.8
    assert truck.weight_t == 25


def test_forbidden_overweight_and_too_wide_vehicle_gets_major_penalty() -> None:
    breakdown = RouteScoringService().score(
        _route(),
        RouteLocalFactors(
            requested_vehicle_profile="truck",
            vehicle_width_m=2.8,
            vehicle_weight_t=25,
            vehicle_forbidden=True,
            vehicle_overweight=True,
            vehicle_too_wide=True,
        ),
    )

    assert breakdown.vehicle_penalty == 25_000
    assert breakdown.total_score > 25_000


def test_compatible_vehicle_does_not_get_constraint_penalty() -> None:
    breakdown = RouteScoringService().score(
        _route(),
        RouteLocalFactors(
            requested_vehicle_profile="motorcycle",
            vehicle_width_m=0.9,
            vehicle_weight_t=0.5,
        ),
    )

    assert breakdown.vehicle_penalty == 0
