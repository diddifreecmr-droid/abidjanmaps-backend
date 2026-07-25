from dataclasses import dataclass

from app.modules.routing.domain.entities.route import Route


@dataclass(frozen=True)
class RouteLocalFactors:
    blocked: bool = False
    degraded: bool = False
    flood_risk: bool = False
    control_point: bool = False
    unsafe_night: bool = False
    narrow_width: bool = False
    toll_present: bool = False
    requested_vehicle_profile: str = "car"
    vehicle_width_m: float = 1.9
    vehicle_weight_t: float = 2.5
    vehicle_forbidden: bool = False
    vehicle_overweight: bool = False
    vehicle_too_wide: bool = False
    seasonal_risk_multiplier: float = 1.0
    vehicle_profile_multiplier: float = 1.0


@dataclass(frozen=True)
class RouteScoreBreakdown:
    base_score: float
    distance_component: float
    duration_component: float
    blocked_penalty: float
    degraded_penalty: float
    flood_penalty: float
    control_penalty: float
    unsafe_night_penalty: float
    narrow_width_penalty: float
    toll_penalty: float
    seasonal_penalty: float
    vehicle_penalty: float
    total_score: float


@dataclass(frozen=True)
class ScoredRoute:
    route: Route
    score: float
    rank: int
    breakdown: RouteScoreBreakdown


class RouteScoringService:
    def score(self, route: Route, factors: RouteLocalFactors | None = None) -> RouteScoreBreakdown:
        factors = factors or RouteLocalFactors()
        distance_component = route.distance_m / 100.0
        duration_component = route.duration_s
        base_score = duration_component + distance_component
        blocked_penalty = 10_000.0 if factors.blocked else 0.0
        degraded_penalty = 250.0 if factors.degraded else 0.0
        flood_penalty = 400.0 if factors.flood_risk else 0.0
        control_penalty = 60.0 if factors.control_point else 0.0
        unsafe_night_penalty = 180.0 if factors.unsafe_night else 0.0
        narrow_width_penalty = 200.0 if factors.narrow_width else 0.0
        toll_penalty = 35.0 if factors.toll_present else 0.0
        seasonal_penalty = base_score * max(factors.seasonal_risk_multiplier - 1.0, 0.0)
        vehicle_penalty = (
            base_score * max(factors.vehicle_profile_multiplier - 1.0, 0.0)
            + (10_000.0 if factors.vehicle_forbidden else 0.0)
            + (10_000.0 if factors.vehicle_overweight else 0.0)
            + (5_000.0 if factors.vehicle_too_wide else 0.0)
        )
        total_score = round(
            base_score
            + blocked_penalty
            + degraded_penalty
            + flood_penalty
            + control_penalty
            + unsafe_night_penalty
            + narrow_width_penalty
            + toll_penalty
            + seasonal_penalty
            + vehicle_penalty,
            2,
        )
        return RouteScoreBreakdown(
            base_score=round(base_score, 2),
            distance_component=round(distance_component, 2),
            duration_component=round(duration_component, 2),
            blocked_penalty=blocked_penalty,
            degraded_penalty=degraded_penalty,
            flood_penalty=flood_penalty,
            control_penalty=control_penalty,
            unsafe_night_penalty=unsafe_night_penalty,
            narrow_width_penalty=narrow_width_penalty,
            toll_penalty=toll_penalty,
            seasonal_penalty=round(seasonal_penalty, 2),
            vehicle_penalty=round(vehicle_penalty, 2),
            total_score=total_score,
        )

    def rank_routes(
        self,
        routes: list[Route],
        factors: list[RouteLocalFactors] | None = None,
    ) -> list[ScoredRoute]:
        route_factors = factors or [RouteLocalFactors() for _ in routes]
        scored = []
        for route, factor in zip(routes, route_factors, strict=False):
            breakdown = self.score(route, factor)
            scored.append(ScoredRoute(route=route, score=breakdown.total_score, rank=0, breakdown=breakdown))
        scored.sort(key=lambda item: item.score)
        return [
            ScoredRoute(route=item.route, score=item.score, rank=index + 1, breakdown=item.breakdown)
            for index, item in enumerate(scored)
        ]
