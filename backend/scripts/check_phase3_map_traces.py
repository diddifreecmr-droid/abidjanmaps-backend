import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


def _env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


API_BASE_URL = (_env_value("BACKEND_BASE_URL", "http://127.0.0.1:8000") or "").rstrip("/")
EMAIL = _env_value("PHASE3_TEST_EMAIL") or _env_value("ABIDJANMAPS_TEST_EMAIL")
PASSWORD = _env_value("PHASE3_TEST_PASSWORD") or _env_value("ABIDJANMAPS_TEST_PASSWORD")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _post_json(
    client: httpx.Client,
    path: str,
    payload: dict[str, Any],
    *,
    token: str | None = None,
) -> Any:
    response = client.post(
        f"{API_BASE_URL}{path}",
        json=payload,
        headers=_auth_headers(token) if token else None,
    )
    response.raise_for_status()
    return response.json()


def _get_json(client: httpx.Client, path: str, *, token: str) -> Any:
    response = client.get(f"{API_BASE_URL}{path}", headers=_auth_headers(token))
    response.raise_for_status()
    return response.json()


def _login(client: httpx.Client) -> str:
    if not EMAIL or not PASSWORD:
        raise SystemExit(
            "Missing credentials. Set PHASE3_TEST_EMAIL and PHASE3_TEST_PASSWORD "
            "or ABIDJANMAPS_TEST_EMAIL and ABIDJANMAPS_TEST_PASSWORD."
        )
    body = _post_json(
        client,
        "/api/v1/auth/login",
        {"email": EMAIL, "password": PASSWORD},
    )
    token = body.get("access_token")
    if not token:
        raise AssertionError("Login response did not include access_token")
    return token


def run_checks() -> dict[str, Any]:
    with httpx.Client(timeout=30) as client:
        token = _login(client)
        random_seed = uuid.uuid4().int
        lng_offset = (random_seed % 9000) / 100000
        lat_offset = ((random_seed // 10000) % 9000) / 100000

        started = _post_json(
            client,
            "/api/v1/map-traces/start",
            {
                "start": {
                    "lng": round(-4.02003 + lng_offset, 6),
                    "lat": round(5.3329 + lat_offset, 6),
                },
                "end": {
                    "lng": round(-4.0178 + lng_offset, 6),
                    "lat": round(5.3344 + lat_offset, 6),
                },
                "profile": "car",
                "planned_distance_m": 250,
                "planned_duration_s": 120,
                "planned_route_geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [
                            round(-4.02003 + lng_offset, 6),
                            round(5.3329 + lat_offset, 6),
                        ],
                        [
                            round(-4.0194 + lng_offset, 6),
                            round(5.3334 + lat_offset, 6),
                        ],
                        [
                            round(-4.0186 + lng_offset, 6),
                            round(5.3339 + lat_offset, 6),
                        ],
                        [
                            round(-4.0178 + lng_offset, 6),
                            round(5.3344 + lat_offset, 6),
                        ],
                    ],
                },
            },
            token=token,
        )
        trace_id = started["id"]
        started_at = _parse_datetime(started["started_at"])

        positions_payload = {
            "positions": [
                {
                    "lng": round(-4.02003 + lng_offset, 6),
                    "lat": round(5.3329 + lat_offset, 6),
                    "accuracy_m": 8,
                    "speed_mps": 2.1,
                    "recorded_at": _iso(started_at + timedelta(seconds=0)),
                },
                {
                    "lng": round(-4.0194 + lng_offset, 6),
                    "lat": round(5.3334 + lat_offset, 6),
                    "accuracy_m": 9,
                    "speed_mps": 2.4,
                    "recorded_at": _iso(started_at + timedelta(seconds=45)),
                },
                {
                    "lng": round(-4.0186 + lng_offset, 6),
                    "lat": round(5.3339 + lat_offset, 6),
                    "accuracy_m": 7,
                    "speed_mps": 2.8,
                    "recorded_at": _iso(started_at + timedelta(seconds=95)),
                },
                {
                    "lng": round(-4.0178 + lng_offset, 6),
                    "lat": round(5.3344 + lat_offset, 6),
                    "accuracy_m": 8,
                    "speed_mps": 2.3,
                    "recorded_at": _iso(started_at + timedelta(seconds=180)),
                },
            ]
        }
        positions = _post_json(
            client,
            f"/api/v1/map-traces/{trace_id}/positions",
            positions_payload,
            token=token,
        )
        assert len(positions) == 4, "Expected all GPS positions to be stored"

        finished = _post_json(
            client,
            f"/api/v1/map-traces/{trace_id}/finish",
            {"finished_at": _iso(started_at + timedelta(seconds=180))},
            token=token,
        )
        assert finished["status"] == "finished"
        assert finished["actual_distance_m"] > 0
        assert finished["actual_duration_s"] == 180

        detail = _get_json(client, f"/api/v1/map-traces/{trace_id}", token=token)
        assert len(detail["positions"]) == 4

        analysis = _post_json(
            client,
            f"/api/v1/map-traces/{trace_id}/analyze",
            {},
            token=token,
        )
        assert analysis["trace_id"] == trace_id
        assert "journey_id" not in analysis
        assert analysis["points_count"] == 4
        assert analysis["usable_points_count"] == 4
        assert 0 <= analysis["quality_score"] <= 1
        assert analysis["actual_distance_m"] > 0
        assert analysis["actual_duration_s"] == 180
        assert analysis["average_speed_kmh"] > 0

        saved_analysis = _get_json(
            client,
            f"/api/v1/map-traces/{trace_id}/analysis",
            token=token,
        )
        assert saved_analysis["id"] == analysis["id"]

        insights = _get_json(
            client,
            "/api/v1/map-trace-insights?status=proposed",
            token=token,
        )
        matching_insights = [
            insight for insight in insights if insight["trace_id"] == trace_id
        ]
        evidence_target_trace_id = trace_id
        reused_existing_insight = False
        if not matching_insights:
            all_insights = _get_json(
                client,
                "/api/v1/map-trace-insights?sort=newest&order=desc",
                token=token,
            )
            matching_insights = [
                insight
                for insight in all_insights
                if insight["latest_evidence_trace_id"] == trace_id
            ]
            reused_existing_insight = bool(matching_insights)
        assert matching_insights, (
            "Expected a new proposed insight or an existing insight updated with "
            "latest_evidence_trace_id for the trace"
        )
        reviewed = _post_json(
            client,
            f"/api/v1/map-trace-insights/{matching_insights[0]['id']}/validate",
            {"note": "Validated by Phase 3 API check."},
            token=token,
        )
        assert reviewed["status"] == "validated"
        assert reviewed["duplicate_key"], "Expected reviewed insight to include duplicate_key"
        assert reviewed["evidence_count"] >= 1
        insight_detail = _get_json(
            client,
            f"/api/v1/map-trace-insights/{reviewed['id']}/detail",
            token=token,
        )
        assert insight_detail["trace_id"] == reviewed["trace_id"]
        assert insight_detail["trace"]["id"] == reviewed["trace_id"]
        assert insight_detail["analysis"]["trace_id"] == reviewed["trace_id"]
        if reused_existing_insight:
            assert reviewed["latest_evidence_trace_id"] == evidence_target_trace_id
        conversion = _post_json(
            client,
            f"/api/v1/map-trace-insights/{reviewed['id']}/convert-to-route-report",
            {},
            token=token,
        )
        assert conversion["route_report"]["validation_status"] == "proposed"
        assert conversion["route_report"]["extra_metadata"]["source"] == "map_trace_insight"
        review_queue = _get_json(
            client,
            "/api/v1/map-trace-insights/review-queue",
            token=token,
        )
        assert isinstance(review_queue, list), "Expected review queue to return a list"
        route_report_candidates = _get_json(
            client,
            "/api/v1/map-trace-insights/route-report-candidates",
            token=token,
        )
        assert isinstance(
            route_report_candidates,
            list,
        ), "Expected route report candidates to return a list"

        return {
            "status": "ok",
            "trace_id": trace_id,
            "lng_offset": round(lng_offset, 3),
            "lat_offset": round(lat_offset, 3),
            "positions_count": len(positions),
            "actual_distance_m": finished["actual_distance_m"],
            "actual_duration_s": finished["actual_duration_s"],
            "analysis": {
                "quality_score": analysis["quality_score"],
                "quality_label": analysis["quality_label"],
                "average_speed_kmh": analysis["average_speed_kmh"],
                "phone_average_speed_kmh": analysis["phone_average_speed_kmh"],
                "moving_time_s": analysis["moving_time_s"],
                "stopped_time_s": analysis["stopped_time_s"],
                "max_speed_kmh": analysis["max_speed_kmh"],
                "gps_gap_count": analysis["gps_gap_count"],
                "suspicious_jump_count": analysis["suspicious_jump_count"],
                "recommendation": analysis["recommendation"],
                "events_count": len(analysis["detected_events"]),
            },
            "insight": {
                "id": reviewed["id"],
                "type": reviewed["insight_type"],
                "status": reviewed["status"],
                "confidence_score": reviewed["confidence_score"],
                "duplicate_key": reviewed["duplicate_key"],
                "evidence_count": reviewed["evidence_count"],
                "latest_evidence_trace_id": reviewed["latest_evidence_trace_id"],
                "reused_existing_insight": reused_existing_insight,
                "detail_loaded": True,
            },
            "route_report": {
                "id": conversion["route_report"]["id"],
                "report_type": conversion["route_report"]["report_type"],
                "validation_status": conversion["route_report"]["validation_status"],
            },
            "admin_review": {
                "review_queue_count": len(review_queue),
                "route_report_candidates_count": len(route_report_candidates),
            },
        }


if __name__ == "__main__":
    print(json.dumps(run_checks(), ensure_ascii=True))
