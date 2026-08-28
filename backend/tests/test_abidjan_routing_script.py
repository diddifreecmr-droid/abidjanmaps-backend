from scripts import check_abidjan_routing


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def get(self, url):
        assert url.endswith("/api/v1/health")
        return FakeResponse({"status": "ok", "routing_engine": "available"})

    def post(self, url, json):
        assert url.endswith("/api/v1/routes/proposals/detail")
        return FakeResponse(
            {
                "status": "ok",
                "proposals": [
                    {
                        "rank": 1,
                        "score": 610.5,
                        "route": {
                            "distance_m": 12300,
                            "duration_s": 1800,
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [[-4.084, 5.3367], [-4.016, 5.3204]],
                            },
                        },
                        "price": {"amount": 3200, "currency": "XOF"},
                        "score_breakdown": {
                            "vehicle_constraints": {"eligible": True}
                        },
                        "enrichment": {"factors": {}, "troncons": [], "reports": []},
                    }
                ],
            }
        )


def test_abidjan_routing_script_returns_json_report(monkeypatch) -> None:
    monkeypatch.setattr(check_abidjan_routing.httpx, "Client", lambda timeout: FakeClient())
    monkeypatch.setattr(
        check_abidjan_routing,
        "ABIDJAN_ROUTE_CASES",
        [
            {
                "name": "test_route",
                "label": "Test Route",
                "start": {"lat": 5.3367, "lng": -4.0840},
                "end": {"lat": 5.3204, "lng": -4.0160},
                "expected_distance_km": {"min": 6, "max": 25},
                "expected_duration_min": {"min": 8, "max": 90},
            }
        ],
    )

    report = check_abidjan_routing.run_checks()

    assert report["status"] == "ok"
    assert report["summary"] == {"total": 1, "ok": 1, "error": 0}
    assert report["checks"][0]["name"] == "test_route"
    assert report["checks"][0]["distance_km"] == 12.3
    assert report["checks"][0]["duration_min"] == 30
    assert report["checks"][0]["vehicle_eligible"] is True
