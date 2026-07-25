from __future__ import annotations

ROUTE_REPORT_TYPES = {
    "blocked",
    "road_blocked",
    "degraded",
    "damage",
    "flood",
    "inondation",
    "flood_risk",
    "control_point",
    "checkpoint",
    "checkpoint_delay",
    "unsafe_night",
    "night_risk",
    "security_night",
    "toll",
    "peage",
}


def normalize_route_report_type(value: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_")
    aliases = {
        "road_block": "blocked",
        "road_closed": "blocked",
        "water": "flood",
        "checkpoint": "control_point",
        "controle": "control_point",
        "peage": "toll",
        "night": "unsafe_night",
    }
    return aliases.get(normalized, normalized)


def route_report_taxonomy_documentation() -> dict:
    return {"route_report_type": sorted(ROUTE_REPORT_TYPES)}
