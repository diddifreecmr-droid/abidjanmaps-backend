import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


SEED_FILE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "modules"
    / "map_data"
    / "infrastructure"
    / "seed_data"
    / "phase2_roads.json"
)
API_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _ok(name: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"check": name, "status": "ok", **(extra or {})}


def _get_json(client: httpx.Client, path: str) -> Any:
    response = client.get(f"{API_BASE_URL}{path}")
    response.raise_for_status()
    return response.json()


def _post_json(client: httpx.Client, path: str, payload: dict[str, Any]) -> Any:
    response = client.post(f"{API_BASE_URL}{path}", json=payload)
    response.raise_for_status()
    return response.json()


def run_checks() -> list[dict[str, Any]]:
    fixture = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    route_request = fixture["route_request"]
    checks: list[dict[str, Any]] = []

    with httpx.Client(timeout=30) as client:
        health = _get_json(client, "/api/v1/health")
        assert health["status"] == "ok"
        checks.append(_ok("health", {"routing_engine": health.get("routing_engine")}))

        db_health = _get_json(client, "/api/v1/db-health")
        assert db_health["status"] == "ok"
        checks.append(_ok("db-health", {"database": db_health.get("database")}))

        roads = _get_json(client, "/api/v1/roads")
        assert isinstance(roads, list)
        assert roads, "Expected at least one seeded road"
        assert any(road.get("geometry") for road in roads), "Roads must expose geometry"
        checks.append(_ok("roads", {"count": len(roads)}))

        first_road_name = roads[0]["name"]
        geocoding = _get_json(
            client,
            f"/api/v1/geocoding/search?q={quote(first_road_name)}",
        )
        assert isinstance(geocoding, list)
        assert geocoding, "Expected geocoding search to find at least one road/place"
        assert geocoding[0].get("location") is not None
        checks.append(_ok("geocoding-search", {"count": len(geocoding)}))

        places = _get_json(client, "/api/v1/places")
        assert isinstance(places, list)
        checks.append(_ok("places", {"count": len(places)}))

        reports = _get_json(client, "/api/v1/route-reports")
        assert isinstance(reports, list)
        checks.append(_ok("route-reports", {"count": len(reports)}))

        proposals = _post_json(
            client,
            "/api/v1/routes/proposals/detail",
            {
                **route_request,
                "profile": "car",
                "vehicle_width_m": 1.9,
                "vehicle_weight_t": 2.5,
            },
        )
        items = proposals["proposals"]
        assert items, "Expected at least one route proposal"
        assert items[0]["rank"] == 1
        assert items[0]["score_breakdown"]["vehicle_constraints"]["eligible"] is True
        assert items[0].get("enrichment") is not None
        checks.append(
            _ok(
                "route-proposals-detail",
                {
                    "count": len(items),
                    "best_score": items[0]["score"],
                },
            )
        )

    return checks


if __name__ == "__main__":
    print(json.dumps(run_checks(), ensure_ascii=True))
