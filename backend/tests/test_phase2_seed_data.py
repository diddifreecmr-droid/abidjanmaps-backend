import json
from pathlib import Path

from app.modules.map_data.domain.entities.road import Road


SEED_FILE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "modules"
    / "map_data"
    / "infrastructure"
    / "seed_data"
    / "phase2_roads.json"
)


def test_phase2_seed_roads_are_valid_and_unique() -> None:
    payload = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    seed_keys = [item["seed_key"] for item in payload["roads"]]

    assert len(payload["roads"]) == 4
    assert len(seed_keys) == len(set(seed_keys))

    roads = [
        Road(
            name=item["name"],
            geometry=item["geometry"],
            surface_state=item["surface_state"],
            seasonal_practicability=item["seasonal_practicability"],
            tonnage_max_reel_t=item["tonnage_max_reel_t"],
            width_usable_m=item["width_usable_m"],
            type_flux=item["type_flux"],
            allowed_vehicle_profiles=item["allowed_vehicle_profiles"],
        )
        for item in payload["roads"]
    ]

    assert any(road.allowed_vehicle_profiles == ["motorcycle"] for road in roads)
    assert any((road.tonnage_max_reel_t or 0) >= 35 for road in roads)
    assert any(road.type_flux == "toll" for road in roads)
