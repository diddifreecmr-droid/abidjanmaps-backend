from dataclasses import dataclass


VEHICLE_PROFILE_SPECS = {
    "car": {
        "default_width_m": 1.9,
        "default_weight_t": 2.5,
        "recommended_road_width_m": 3.0,
    },
    "motorcycle": {
        "default_width_m": 0.9,
        "default_weight_t": 0.5,
        "recommended_road_width_m": 1.5,
    },
    "truck": {
        "default_width_m": 2.6,
        "default_weight_t": 19.0,
        "recommended_road_width_m": 3.5,
    },
}
VEHICLE_PROFILES = frozenset(VEHICLE_PROFILE_SPECS)


def normalize_vehicle_profile(value: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_")
    aliases = {
        "voiture": "car",
        "auto": "car",
        "moto": "motorcycle",
        "motorbike": "motorcycle",
        "camion": "truck",
        "poids_lourd": "truck",
    }
    profile = aliases.get(normalized, normalized)
    if profile not in VEHICLE_PROFILES:
        raise ValueError(f"Unsupported vehicle profile: {value}")
    return profile


def normalize_vehicle_profiles(values: list[str]) -> list[str]:
    normalized = [normalize_vehicle_profile(value) for value in values]
    return list(dict.fromkeys(normalized))


@dataclass(frozen=True)
class VehicleContext:
    profile: str
    width_m: float
    weight_t: float
    recommended_road_width_m: float


def build_vehicle_context(
    profile: str,
    width_m: float | None = None,
    weight_t: float | None = None,
) -> VehicleContext:
    normalized_profile = normalize_vehicle_profile(profile)
    specs = VEHICLE_PROFILE_SPECS[normalized_profile]
    return VehicleContext(
        profile=normalized_profile,
        width_m=width_m if width_m is not None else specs["default_width_m"],
        weight_t=weight_t if weight_t is not None else specs["default_weight_t"],
        recommended_road_width_m=specs["recommended_road_width_m"],
    )


def vehicle_taxonomy_documentation() -> dict:
    return {
        profile: dict(specifications)
        for profile, specifications in VEHICLE_PROFILE_SPECS.items()
    }
