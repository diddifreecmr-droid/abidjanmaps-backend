import httpx

from app.modules.routing.domain.entities.coordinate import Coordinate
from app.shared.configuration.settings import settings
from app.modules.routing.infrastructure.osrm.engine import OSRMRoutingEngine


class FakeResponse:
    status_code = 200

    def json(self) -> dict:
        return {
            "routes": [
                {
                    "geometry": {"type": "LineString", "coordinates": [[-4.0, 5.3], [-3.9, 5.4]]},
                    "distance": 1450,
                    "duration": 360,
                }
            ]
        }


def test_osrm_engine_parses_valid_response(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("app.modules.routing.infrastructure.osrm.engine.httpx.get", fake_get)
    monkeypatch.setattr(settings, "osrm_base_url", "http://osrm:5000")
    monkeypatch.setattr(settings, "osrm_username", None)
    monkeypatch.setattr(settings, "osrm_password", None)

    engine = OSRMRoutingEngine()
    route = engine.calculate_route(
        Coordinate(lat=5.3329, lng=-4.02003),
        Coordinate(lat=5.33892, lng=-3.97754),
        profile="car",
        request_id="abc",
    )

    assert route.distance_m == 1450
    assert route.duration_s == 360
    assert route.geometry["type"] == "LineString"
