from scripts import validate_staging


def test_validate_staging_public_mode_skips_phase3(monkeypatch) -> None:
    monkeypatch.setenv("VALIDATE_STAGING_MODE", "public")
    monkeypatch.setenv("BACKEND_BASE_URL", "https://staging.example.test")
    monkeypatch.delenv("PHASE3_TEST_EMAIL", raising=False)
    monkeypatch.delenv("PHASE3_TEST_PASSWORD", raising=False)
    monkeypatch.setattr(
        validate_staging.check_staging_public_api,
        "run_checks",
        lambda: [{"check": "health", "status": "ok"}],
    )
    monkeypatch.setattr(
        validate_staging.check_abidjan_routing,
        "run_checks",
        lambda: {"status": "ok", "summary": {"total": 1, "ok": 1, "error": 0}},
    )

    result = validate_staging.run_validation()

    assert result["status"] == "ok"
    assert result["base_url"] == "https://staging.example.test"
    assert result["checks"][0]["name"] == "public-api"
    assert result["checks"][1]["name"] == "abidjan-routing"
    assert result["checks"][2]["name"] == "phase3-map-traces"
    assert result["checks"][2]["status"] == "skipped"


def test_validate_staging_full_mode_requires_phase3_credentials(monkeypatch) -> None:
    monkeypatch.setenv("VALIDATE_STAGING_MODE", "full")
    monkeypatch.delenv("PHASE3_TEST_EMAIL", raising=False)
    monkeypatch.delenv("PHASE3_TEST_PASSWORD", raising=False)
    monkeypatch.delenv("ABIDJANMAPS_TEST_EMAIL", raising=False)
    monkeypatch.delenv("ABIDJANMAPS_TEST_PASSWORD", raising=False)
    monkeypatch.setattr(
        validate_staging.check_staging_public_api,
        "run_checks",
        lambda: [{"check": "health", "status": "ok"}],
    )
    monkeypatch.setattr(
        validate_staging.check_abidjan_routing,
        "run_checks",
        lambda: {"status": "ok", "summary": {"total": 1, "ok": 1, "error": 0}},
    )

    result = validate_staging.run_validation()

    assert result["status"] == "error"
    assert result["checks"][1]["name"] == "abidjan-routing"
    assert result["checks"][2]["name"] == "phase3-map-traces"
    assert result["checks"][2]["status"] == "error"
    assert "Missing PHASE3_TEST_EMAIL" in result["checks"][2]["message"]


def test_validate_staging_full_mode_runs_phase3_when_credentials_exist(monkeypatch) -> None:
    monkeypatch.setenv("VALIDATE_STAGING_MODE", "full")
    monkeypatch.setenv("PHASE3_TEST_EMAIL", "admin@example.com")
    monkeypatch.setenv("PHASE3_TEST_PASSWORD", "secret")
    monkeypatch.setattr(
        validate_staging.check_staging_public_api,
        "run_checks",
        lambda: [{"check": "health", "status": "ok"}],
    )
    monkeypatch.setattr(
        validate_staging.check_abidjan_routing,
        "run_checks",
        lambda: {"status": "ok", "summary": {"total": 1, "ok": 1, "error": 0}},
    )
    monkeypatch.setattr(
        validate_staging.check_phase3_map_traces,
        "run_checks",
        lambda: {"status": "ok", "trace_id": 1},
    )

    result = validate_staging.run_validation()

    assert result["status"] == "ok"
    assert result["checks"][0]["name"] == "public-api"
    assert result["checks"][1]["name"] == "abidjan-routing"
    assert result["checks"][2]["name"] == "phase3-map-traces"
    assert result["checks"][2]["data"]["trace_id"] == 1
