from fastapi.testclient import TestClient

from app.main import app
from app.modules.map_data.presentation import places_api as places_module


client = TestClient(app)


class FakePlace:
    def __init__(self, place_id: int, name: str, category: str, aliases: list[str], description: str | None, verified: bool, extra_metadata: dict) -> None:
        self.id = place_id
        self.name = name
        self.category = category
        self.aliases = aliases
        self.description = description
        self.verified = verified
        self.extra_metadata = extra_metadata


class FakePlaceRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def search(
        self,
        query: str,
        *,
        limit: int | None = None,
        bias_lat: float | None = None,
        bias_lng: float | None = None,
    ):
        return [
            FakePlace(1, "Carrefour Anador", "landmark", ["Anador", "Carrefour Anador Yopougon"], "Repere local", True, {})
        ] if "anador" in query.lower() else []


def test_search_places_by_name() -> None:
    app.dependency_overrides[places_module.get_async_session] = lambda: object()
    places_module.SQLAlchemyPlaceRepository = FakePlaceRepository
    try:
        response = client.get("/api/v1/places/search?q=Anador")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Carrefour Anador"
