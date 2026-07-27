import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.modules.journeys.application.use_cases.manage_journeys import JourneyService
from app.modules.journeys.domain.entities.journey import Journey, JourneyDetail, JourneyPosition
from app.modules.journeys.presentation.api import get_journey_service
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user


client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides.clear()


def teardown_function() -> None:
    app.dependency_overrides.clear()


async def fake_current_user() -> User:
    return User(id=42, email="collector@example.com", role="user")


class FakeJourneyService:
    def __init__(self) -> None:
        self.positions: list[JourneyPosition] = []

    async def start_journey(self, journey: Journey) -> Journey:
        return Journey(
            id=1,
            user_id=journey.user_id,
            status="started",
            profile=journey.profile,
            start_location=journey.start_location,
            end_location=journey.end_location,
            planned_distance_m=journey.planned_distance_m,
            planned_duration_s=journey.planned_duration_s,
            planned_route_geometry=journey.planned_route_geometry,
            started_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
        )

    async def add_positions(
        self,
        *,
        journey_id: int,
        user_id: int,
        positions: list[JourneyPosition],
    ) -> list[JourneyPosition]:
        self.positions = [
            JourneyPosition(
                id=index + 1,
                journey_id=journey_id,
                location=position.location,
                accuracy_m=position.accuracy_m,
                speed_mps=position.speed_mps,
                recorded_at=position.recorded_at,
            )
            for index, position in enumerate(positions)
        ]
        return self.positions

    async def finish_journey(
        self,
        *,
        journey_id: int,
        user_id: int,
        finished_at: datetime | None = None,
    ) -> Journey:
        return Journey(
            id=journey_id,
            user_id=user_id,
            status="finished",
            profile="car",
            start_location={"lng": -4.02, "lat": 5.33},
            end_location={"lng": -3.99, "lat": 5.34},
            actual_distance_m=1200.5,
            actual_duration_s=900,
            started_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
            finished_at=finished_at,
        )

    async def get_journey(self, *, journey_id: int, user_id: int) -> JourneyDetail:
        return JourneyDetail(
            journey=Journey(
                id=journey_id,
                user_id=user_id,
                status="started",
                profile="car",
                start_location={"lng": -4.02, "lat": 5.33},
                end_location={"lng": -3.99, "lat": 5.34},
            ),
            positions=self.positions,
        )

    async def list_journeys(self, *, user_id: int) -> list[Journey]:
        return [
            Journey(
                id=1,
                user_id=user_id,
                status="started",
                profile="car",
                start_location={"lng": -4.02, "lat": 5.33},
                end_location={"lng": -3.99, "lat": 5.34},
            )
        ]


def test_journey_start_requires_authentication() -> None:
    response = client.post(
        "/api/v1/journeys/start",
        json={
            "start": {"lng": -4.02, "lat": 5.33},
            "end": {"lng": -3.99, "lat": 5.34},
            "profile": "car",
        },
    )

    assert response.status_code == 401


def test_journey_collection_workflow() -> None:
    service = FakeJourneyService()
    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_journey_service] = lambda: service

    start_response = client.post(
        "/api/v1/journeys/start",
        json={
            "start": {"lng": -4.02, "lat": 5.33},
            "end": {"lng": -3.99, "lat": 5.34},
            "profile": "moto",
            "planned_distance_m": 1500,
            "planned_duration_s": 360,
        },
    )
    assert start_response.status_code == 201
    assert start_response.json()["profile"] == "motorcycle"

    positions_response = client.post(
        "/api/v1/journeys/1/positions",
        json={
            "positions": [
                {
                    "lng": -4.019,
                    "lat": 5.331,
                    "accuracy_m": 8,
                    "speed_mps": 6.2,
                    "recorded_at": "2026-07-27T10:01:00Z",
                }
            ]
        },
    )
    assert positions_response.status_code == 201
    assert positions_response.json()[0]["location"] == {"lng": -4.019, "lat": 5.331}

    detail_response = client.get("/api/v1/journeys/1")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["positions"]) == 1

    finish_response = client.post(
        "/api/v1/journeys/1/finish",
        json={"finished_at": "2026-07-27T10:15:00Z"},
    )
    assert finish_response.status_code == 200
    assert finish_response.json()["status"] == "finished"
    assert finish_response.json()["actual_distance_m"] == 1200.5


def test_journey_service_computes_actual_summary() -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.finished: Journey | None = None

        async def create(self, journey: Journey) -> Journey:
            return journey

        async def add_positions(self, journey_id: int, positions: list[JourneyPosition]):
            return positions

        async def get_detail(self, journey_id: int, user_id: int):
            return JourneyDetail(
                journey=Journey(
                    id=journey_id,
                    user_id=user_id,
                    status="started",
                    profile="car",
                    start_location={"lng": -4.02, "lat": 5.33},
                    end_location={"lng": -3.99, "lat": 5.34},
                    started_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                ),
                positions=[
                    JourneyPosition(
                        id=1,
                        journey_id=journey_id,
                        location={"lng": -4.02, "lat": 5.33},
                        recorded_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=2,
                        journey_id=journey_id,
                        location={"lng": -4.019, "lat": 5.331},
                        recorded_at=datetime(2026, 7, 27, 10, 5, tzinfo=timezone.utc),
                    ),
                ],
            )

        async def list_for_user(self, user_id: int):
            return []

        async def finish(
            self,
            journey_id: int,
            user_id: int,
            *,
            finished_at: datetime,
            actual_distance_m: float,
            actual_duration_s: int,
        ):
            self.finished = Journey(
                id=journey_id,
                user_id=user_id,
                status="finished",
                profile="car",
                start_location={"lng": -4.02, "lat": 5.33},
                end_location={"lng": -3.99, "lat": 5.34},
                actual_distance_m=actual_distance_m,
                actual_duration_s=actual_duration_s,
                finished_at=finished_at,
            )
            return self.finished

    repository = FakeRepository()
    journey = asyncio.run(
        JourneyService(repository).finish_journey(
            journey_id=1,
            user_id=42,
            finished_at=datetime(2026, 7, 27, 10, 15, tzinfo=timezone.utc),
        )
    )

    assert journey.status == "finished"
    assert journey.actual_duration_s == 900
    assert journey.actual_distance_m is not None
    assert journey.actual_distance_m > 100
