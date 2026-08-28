from scripts import check_staging_public_api


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self) -> None:
        self.requested_urls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def get(self, url):
        self.requested_urls.append(url)
        if url.endswith("/api/v1/health"):
            return FakeResponse({"status": "ok", "routing_engine": "available"})
        if url.endswith("/api/v1/db-health"):
            return FakeResponse({"status": "ok", "database": "available"})
        if "/api/v1/roads/search?" in url:
            return FakeResponse(
                [
                    {
                        "id": 1,
                        "name": "Demo Alt 1 - passage voiture et moto",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[-4.02, 5.33], [-4.01, 5.34]],
                        },
                    }
                ]
            )
        if "/api/v1/geocoding/autocomplete?" in url:
            return FakeResponse(
                {
                    "status": "ok",
                    "query": "Demo",
                    "count": 1,
                    "results": [
                        {
                            "type": "road",
                            "id": 1,
                            "label": "Demo Alt 1 - passage voiture et moto",
                            "location": {"lng": -4.01, "lat": 5.34},
                        }
                    ],
                }
            )
        if "/api/v1/places/search?" in url:
            return FakeResponse([])
        if url.endswith("/api/v1/route-reports"):
            return FakeResponse([])
        raise AssertionError(f"Unexpected GET URL: {url}")

    def post(self, url, json):
        assert url.endswith("/api/v1/routes/proposals/detail")
        return FakeResponse(
            {
                "status": "ok",
                "proposals": [
                    {
                        "rank": 1,
                        "score": 100.0,
                        "route": {
                            "distance_m": 1000,
                            "duration_s": 300,
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [[-4.02, 5.33], [-4.01, 5.34]],
                            },
                        },
                        "price": {"amount": 1000, "currency": "XOF"},
                        "score_breakdown": {
                            "vehicle_constraints": {"eligible": False}
                        },
                        "enrichment": {"factors": {}, "troncons": [], "reports": []},
                    }
                ],
            }
        )


def test_public_api_check_uses_limited_search_endpoints(monkeypatch) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(
        check_staging_public_api.httpx,
        "Client",
        lambda timeout: fake_client,
    )

    checks = check_staging_public_api.run_checks()

    assert [check["check"] for check in checks] == [
        "health",
        "db-health",
        "roads-search",
        "geocoding-autocomplete",
        "places-search",
        "route-reports",
        "route-proposals-detail",
    ]
    assert not any(url.endswith("/api/v1/roads") for url in fake_client.requested_urls)
    assert not any(url.endswith("/api/v1/places") for url in fake_client.requested_urls)
