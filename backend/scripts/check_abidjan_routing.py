import json
import os
import time
from typing import Any

import httpx


API_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").strip().strip('"').strip("'").rstrip("/")


ABIDJAN_ROUTE_CASES: list[dict[str, Any]] = [
    {
        "name": "yopougon_siporex_to_plateau",
        "label": "Yopougon Siporex -> Plateau",
        "start": {"lat": 5.3367, "lng": -4.0840},
        "end": {"lat": 5.3204, "lng": -4.0160},
        "expected_distance_km": {"min": 6, "max": 25},
        "expected_duration_min": {"min": 8, "max": 90},
    },
    {
        "name": "cocody_riviera_to_plateau",
        "label": "Cocody Riviera -> Plateau",
        "start": {"lat": 5.3575, "lng": -3.9775},
        "end": {"lat": 5.3204, "lng": -4.0160},
        "expected_distance_km": {"min": 5, "max": 25},
        "expected_duration_min": {"min": 8, "max": 90},
    },
    {
        "name": "abobo_to_cocody",
        "label": "Abobo -> Cocody",
        "start": {"lat": 5.4163, "lng": -4.0159},
        "end": {"lat": 5.3555, "lng": -3.9856},
        "expected_distance_km": {"min": 5, "max": 30},
        "expected_duration_min": {"min": 8, "max": 100},
    },
    {
        "name": "airport_to_plateau",
        "label": "Aeroport -> Plateau",
        "start": {"lat": 5.2604, "lng": -3.9263},
        "end": {"lat": 5.3204, "lng": -4.0160},
        "expected_distance_km": {"min": 8, "max": 35},
        "expected_duration_min": {"min": 10, "max": 100},
    },
    {
        "name": "marcory_to_treichville",
        "label": "Marcory -> Treichville",
        "start": {"lat": 5.3017, "lng": -3.9869},
        "end": {"lat": 5.2957, "lng": -4.0042},
        "expected_distance_km": {"min": 2, "max": 18},
        "expected_duration_min": {"min": 4, "max": 60},
    },
    {
        "name": "bingerville_to_plateau",
        "label": "Bingerville -> Plateau",
        "start": {"lat": 5.3558, "lng": -3.8894},
        "end": {"lat": 5.3204, "lng": -4.0160},
        "expected_distance_km": {"min": 10, "max": 45},
        "expected_duration_min": {"min": 15, "max": 120},
    },
]


def _range_check(value: float, expected: dict[str, float]) -> bool:
    return expected["min"] <= value <= expected["max"]


def _post_json(client: httpx.Client, path: str, payload: dict[str, Any]) -> Any:
    response = client.post(f"{API_BASE_URL}{path}", json=payload)
    response.raise_for_status()
    return response.json()


def _get_json(client: httpx.Client, path: str) -> Any:
    response = client.get(f"{API_BASE_URL}{path}")
    response.raise_for_status()
    return response.json()


def _run_case(client: httpx.Client, route_case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    payload = {
        "start": route_case["start"],
        "end": route_case["end"],
        "profile": "car",
        "vehicle_width_m": 1.9,
        "vehicle_weight_t": 2.5,
    }
    body = _post_json(client, "/api/v1/routes/proposals/detail", payload)
    proposals = body.get("proposals", [])
    assert proposals, "Expected at least one route proposal"

    best = proposals[0]
    route = best["route"]
    geometry = route["geometry"]
    coordinates = geometry.get("coordinates", [])
    distance_km = round(route["distance_m"] / 1000, 2)
    duration_min = round(route["duration_s"] / 60, 2)
    distance_ok = _range_check(distance_km, route_case["expected_distance_km"])
    duration_ok = _range_check(duration_min, route_case["expected_duration_min"])
    geojson_ok = geometry.get("type") == "LineString" and len(coordinates) >= 2

    assert distance_ok, f"Unexpected distance_km={distance_km}"
    assert duration_ok, f"Unexpected duration_min={duration_min}"
    assert geojson_ok, "Expected valid LineString geometry"

    return {
        "name": route_case["name"],
        "label": route_case["label"],
        "status": "ok",
        "distance_km": distance_km,
        "duration_min": duration_min,
        "alternatives_count": len(proposals),
        "geojson_valid": geojson_ok,
        "coordinates_count": len(coordinates),
        "best_score": best["score"],
        "best_rank": best["rank"],
        "best_price": best["price"],
        "vehicle_eligible": best["score_breakdown"]["vehicle_constraints"]["eligible"],
        "enrichment_loaded": best.get("enrichment") is not None,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def run_checks() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    with httpx.Client(timeout=45) as client:
        health = _get_json(client, "/api/v1/health")
        assert health["status"] == "ok"
        assert health.get("routing_engine") == "available"

        for route_case in ABIDJAN_ROUTE_CASES:
            try:
                checks.append(_run_case(client, route_case))
            except Exception as exc:
                checks.append(
                    {
                        "name": route_case["name"],
                        "label": route_case["label"],
                        "status": "error",
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                )

    success_count = sum(1 for check in checks if check["status"] == "ok")
    return {
        "status": "ok" if success_count == len(checks) else "error",
        "base_url": API_BASE_URL,
        "summary": {
            "total": len(checks),
            "ok": success_count,
            "error": len(checks) - success_count,
        },
        "checks": checks,
    }


if __name__ == "__main__":
    result = run_checks()
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result["status"] == "ok" else 1)
