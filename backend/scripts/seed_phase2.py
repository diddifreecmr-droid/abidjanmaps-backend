import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.modules.map_data.application.use_cases.update_map_data import UpdateRoad
from app.modules.map_data.domain.entities.road import Road
from app.modules.map_data.infrastructure.persistence.models import RoadORM
from app.modules.map_data.infrastructure.persistence.road_repository import (
    SQLAlchemyRoadRepository,
)
from app.shared.infrastructure.db import async_session_factory


SEED_FILE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "modules"
    / "map_data"
    / "infrastructure"
    / "seed_data"
    / "phase2_roads.json"
)
SEED_ACTOR = "phase2-seed"


def _road_values(item: dict, metadata: dict) -> dict:
    return {
        "name": item["name"],
        "geometry": item["geometry"],
        "surface_state": item["surface_state"],
        "seasonal_practicability": item["seasonal_practicability"],
        "surface_reel": item.get("surface_reel"),
        "tonnage_max_reel_t": item.get("tonnage_max_reel_t"),
        "point_controle": item.get("point_controle"),
        "temps_attente_p50_s": item.get("temps_attente_p50_s"),
        "temps_attente_p90_s": item.get("temps_attente_p90_s"),
        "eclairage": item.get("eclairage"),
        "securite_nuit": item.get("securite_nuit"),
        "width_usable_m": item.get("width_usable_m"),
        "pente_max_pct": item.get("pente_max_pct"),
        "type_flux": item.get("type_flux"),
        "allowed_vehicle_profiles": item["allowed_vehicle_profiles"],
        "is_blocked": item.get("is_blocked", False),
        "extra_metadata": metadata,
    }


async def seed_phase2() -> dict[str, int]:
    payload = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    dataset = payload["dataset"]
    version = payload["version"]
    counters = {"created": 0, "updated": 0, "validated": 0, "skipped": 0}

    async with async_session_factory() as session:
        repository = SQLAlchemyRoadRepository(session)
        updater = UpdateRoad(repository)

        for item in payload["roads"]:
            seed_key = item["seed_key"]
            metadata = {
                "source": dataset,
                "seed_key": seed_key,
                "seed_version": version,
            }
            result = await session.execute(
                select(RoadORM).where(
                    RoadORM.extra_metadata["seed_key"].astext == seed_key
                )
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                values = _road_values(item, metadata)
                road = await repository.create(
                    Road(
                        name=values["name"],
                        geometry=values["geometry"],
                        surface_state=values["surface_state"],
                        seasonal_practicability=values[
                            "seasonal_practicability"
                        ],
                        surface_reel=values["surface_reel"],
                        tonnage_max_reel_t=values["tonnage_max_reel_t"],
                        point_controle=values["point_controle"],
                        temps_attente_p50_s=values["temps_attente_p50_s"],
                        temps_attente_p90_s=values["temps_attente_p90_s"],
                        eclairage=values["eclairage"],
                        securite_nuit=values["securite_nuit"],
                        width_usable_m=values["width_usable_m"],
                        pente_max_pct=values["pente_max_pct"],
                        type_flux=values["type_flux"],
                        allowed_vehicle_profiles=values[
                            "allowed_vehicle_profiles"
                        ],
                        is_blocked=values["is_blocked"],
                        metadata=metadata,
                    )
                )
                existing = await repository.set_validation_status(
                    road.id,
                    "validated",
                    changed_by=SEED_ACTOR,
                    note=f"Validated demo seed {seed_key}",
                )
                counters["created"] += 1
                counters["validated"] += 1
                continue

            current_version = existing.extra_metadata.get("seed_version")
            if current_version != version:
                existing = await updater.execute(
                    road_id=existing.id,
                    changes=_road_values(item, metadata),
                    changed_by=SEED_ACTOR,
                    note=f"Updated demo seed {seed_key} to version {version}",
                )
                counters["updated"] += 1

            if existing.validation_status != "validated":
                await repository.set_validation_status(
                    existing.id,
                    "validated",
                    changed_by=SEED_ACTOR,
                    note=f"Validated demo seed {seed_key}",
                )
                counters["validated"] += 1
            elif current_version == version:
                counters["skipped"] += 1

    return counters


if __name__ == "__main__":
    summary = asyncio.run(seed_phase2())
    print(json.dumps(summary, ensure_ascii=True))
