from dataclasses import dataclass, field

from app.modules.routing.application.services.route_scoring import RouteLocalFactors


@dataclass(frozen=True)
class EnrichmentTroncon:
    road_id: int
    road_name: str
    validation_status: str
    surface_state: str
    seasonal_practicability: str
    is_blocked: bool
    point_controle: str | None
    width_usable_m: float | None
    tonnage_max_reel_t: float | None
    allowed_vehicle_profiles: list[str]
    securite_nuit: int | None
    type_flux: str | None


@dataclass(frozen=True)
class EnrichmentReport:
    id: int
    road_id: int | None
    report_type: str
    severity: int
    message: str


@dataclass(frozen=True)
class RouteEnrichmentDetail:
    factors: RouteLocalFactors
    troncons: list[EnrichmentTroncon] = field(default_factory=list)
    reports: list[EnrichmentReport] = field(default_factory=list)
