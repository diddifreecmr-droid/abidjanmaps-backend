from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.modules.map_data.domain.taxonomy import (
    normalize_road_surface_state,
    normalize_point_controle,
    normalize_seasonal_practicability,
    normalize_type_flux,
)
from app.shared.domain.vehicle import normalize_vehicle_profiles


@dataclass(frozen=True, kw_only=True)
class Road:
    id: int | None = None
    name: str
    geometry: dict[str, Any]
    surface_state: str
    seasonal_practicability: str
    surface_reel: str | None = None
    tonnage_max_reel_t: float | None = None
    point_controle: str | None = None
    temps_attente_p50_s: int | None = None
    temps_attente_p90_s: int | None = None
    eclairage: int | None = None
    securite_nuit: int | None = None
    width_usable_m: float | None = None
    pente_max_pct: float | None = None
    type_flux: str | None = None
    allowed_vehicle_profiles: list[str] = field(
        default_factory=lambda: ["car", "motorcycle", "truck"]
    )
    is_blocked: bool = False
    validation_status: str = "proposed"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "surface_state", normalize_road_surface_state(self.surface_state))
        object.__setattr__(self, "seasonal_practicability", normalize_seasonal_practicability(self.seasonal_practicability))
        object.__setattr__(self, "point_controle", normalize_point_controle(self.point_controle))
        object.__setattr__(self, "type_flux", normalize_type_flux(self.type_flux))
        object.__setattr__(
            self,
            "allowed_vehicle_profiles",
            normalize_vehicle_profiles(self.allowed_vehicle_profiles),
        )
