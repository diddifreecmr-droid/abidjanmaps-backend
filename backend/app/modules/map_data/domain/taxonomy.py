from __future__ import annotations

from app.shared.domain.vehicle import vehicle_taxonomy_documentation

ROAD_SURFACE_STATES = {"good", "fair", "degraded", "bad", "damaged", "poor"}
ROAD_SEASONAL_PRACTICABILITY = {
    "all_year",
    "dry_season_only",
    "rainy_season_only",
    "flood_risk",
    "inondable",
    "wet",
}
ROAD_POINT_CONTROLE = {"none", "checkpoint", "barrier", "customs", "police"}
ROAD_TYPE_FLUX = {"free", "toll", "restricted", "mixed"}


def normalize_road_surface_state(value: str) -> str:
    normalized = (value or "").strip().lower()
    aliases = {
        "ok": "good",
        "stable": "good",
        "passable": "fair",
        "endommage": "damaged",
    }
    return aliases.get(normalized, normalized)


def normalize_seasonal_practicability(value: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_")
    aliases = {
        "all_year_round": "all_year",
        "dry": "dry_season_only",
        "rainy": "rainy_season_only",
        "flooding": "flood_risk",
    }
    return aliases.get(normalized, normalized)


def normalize_point_controle(value: str | None) -> str | None:
    normalized = (value or "").strip().lower().replace(" ", "_")
    if not normalized:
        return None
    aliases = {
        "controle": "checkpoint",
        "control": "checkpoint",
        "post": "checkpoint",
        "barriere": "barrier",
        "douane": "customs",
        "police_station": "police",
    }
    return aliases.get(normalized, normalized)


def normalize_type_flux(value: str | None) -> str | None:
    normalized = (value or "").strip().lower().replace(" ", "_")
    if not normalized:
        return None
    aliases = {
        "peage": "toll",
        "paid": "toll",
        "gratuit": "free",
        "open": "free",
        "limited": "restricted",
    }
    return aliases.get(normalized, normalized)


def road_taxonomy_documentation() -> dict:
    return {
        "surface_state": sorted(ROAD_SURFACE_STATES),
        "seasonal_practicability": sorted(ROAD_SEASONAL_PRACTICABILITY),
        "point_controle": sorted(ROAD_POINT_CONTROLE),
        "type_flux": sorted(ROAD_TYPE_FLUX),
        "vehicle_profiles": vehicle_taxonomy_documentation(),
    }
