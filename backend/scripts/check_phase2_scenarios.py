import json
import os
from pathlib import Path

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


def _constraints(proposal: dict) -> dict:
    return proposal["score_breakdown"]["vehicle_constraints"]


def run_scenarios() -> list[dict]:
    fixture = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    route_request = fixture["route_request"]
    scenarios = (
        ("car", 1.9, 2.5),
        ("motorcycle", 0.9, 0.5),
        ("truck", 2.6, 19.0),
    )
    summaries = []

    with httpx.Client(timeout=30) as client:
        for profile, width_m, weight_t in scenarios:
            response = client.post(
                f"{API_BASE_URL}/api/v1/routes/proposals/detail",
                json={
                    **route_request,
                    "profile": profile,
                    "vehicle_width_m": width_m,
                    "vehicle_weight_t": weight_t,
                },
            )
            response.raise_for_status()
            proposals = response.json()["proposals"]
            constraints = [_constraints(proposal) for proposal in proposals]
            ineligible_count = sum(
                not constraint["eligible"] for constraint in constraints
            )

            assert proposals, f"No proposal returned for {profile}"
            assert constraints[0]["eligible"], (
                f"The first {profile} proposal should be eligible"
            )

            summaries.append(
                {
                    "profile": profile,
                    "best_rank": proposals[0]["rank"],
                    "best_score": proposals[0]["score"],
                    "best_eligible": constraints[0]["eligible"],
                    "ineligible_alternatives": ineligible_count,
                    "detected_reasons": {
                        "forbidden": any(
                            constraint["forbidden"] for constraint in constraints
                        ),
                        "overweight": any(
                            constraint["overweight"] for constraint in constraints
                        ),
                        "too_wide": any(
                            constraint["too_wide"] for constraint in constraints
                        ),
                    },
                }
            )

    return summaries


if __name__ == "__main__":
    print(json.dumps(run_scenarios(), ensure_ascii=True))
