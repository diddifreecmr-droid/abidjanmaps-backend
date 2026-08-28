import asyncio
import json
import os
import time
from typing import Any, Callable

from scripts import (
    check_abidjan_routing,
    check_phase3_map_traces,
    check_staging_public_api,
)
from scripts.seed_phase2 import seed_phase2


def _env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


def _is_enabled(name: str) -> bool:
    return (_env_value(name, "0") or "").lower() in {"1", "true", "yes", "on"}


def _ok(name: str, data: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "ok",
        "data": data,
    }


def _skipped(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "skipped",
        "reason": reason,
    }


def _error(name: str, exc: Exception) -> dict[str, Any]:
    return {
        "name": name,
        "status": "error",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


def _run_step(name: str, callback: Callable[[], Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = _ok(name, callback())
    except Exception as exc:
        result = _error(name, exc)
    result["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


def _run_async_step(name: str, callback: Callable[[], Any]) -> dict[str, Any]:
    return _run_step(name, lambda: asyncio.run(callback()))


def _phase3_credentials_are_available() -> bool:
    email = _env_value("PHASE3_TEST_EMAIL") or _env_value("ABIDJANMAPS_TEST_EMAIL")
    password = _env_value("PHASE3_TEST_PASSWORD") or _env_value(
        "ABIDJANMAPS_TEST_PASSWORD"
    )
    return bool(email and password)


def run_validation() -> dict[str, Any]:
    mode = (_env_value("VALIDATE_STAGING_MODE", "full") or "full").lower()
    if mode not in {"public", "full"}:
        raise SystemExit("VALIDATE_STAGING_MODE must be 'public' or 'full'")

    checks: list[dict[str, Any]] = []
    base_url = _env_value("BACKEND_BASE_URL", "http://127.0.0.1:8000")

    if _is_enabled("VALIDATE_STAGING_SEED_PHASE2"):
        checks.append(_run_async_step("seed-phase2", seed_phase2))

    checks.append(
        _run_step(
            "public-api",
            check_staging_public_api.run_checks,
        )
    )
    checks.append(
        _run_step(
            "abidjan-routing",
            check_abidjan_routing.run_checks,
        )
    )

    if mode == "full":
        if _phase3_credentials_are_available():
            checks.append(
                _run_step(
                    "phase3-map-traces",
                    check_phase3_map_traces.run_checks,
                )
            )
        else:
            checks.append(
                _error(
                    "phase3-map-traces",
                    RuntimeError(
                        "Missing PHASE3_TEST_EMAIL/PHASE3_TEST_PASSWORD. "
                        "Use VALIDATE_STAGING_MODE=public for public-only checks."
                    ),
                )
            )
    else:
        checks.append(
            _skipped(
                "phase3-map-traces",
                "VALIDATE_STAGING_MODE=public",
            )
        )

    overall_status = "ok"
    if any(check["status"] == "error" for check in checks):
        overall_status = "error"

    return {
        "status": overall_status,
        "mode": mode,
        "base_url": base_url,
        "checks": checks,
    }


if __name__ == "__main__":
    result = run_validation()
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result["status"] == "ok" else 1)
