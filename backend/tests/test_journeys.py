import asyncio
import hashlib
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.modules.journeys.presentation import api as journeys_api
from app.modules.journeys.application.use_cases.manage_journeys import (
    JourneyNotFinishedError,
    JourneyNotStartedError,
    JourneyService,
)
from app.modules.journeys.domain.entities.journey import (
    Journey,
    JourneyAnalysis,
    JourneyDetail,
    JourneyPosition,
    MapTraceInsight,
)
from app.modules.journeys.infrastructure.persistence.journey_repository import (
    SQLAlchemyJourneyRepository,
)
from app.modules.journeys.presentation.api import get_journey_service
from app.modules.local_enrichment.domain.entities.route_report import RouteReport
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user
from app.shared.configuration.settings import settings


client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides.clear()


def teardown_function() -> None:
    app.dependency_overrides.clear()


async def fake_current_user() -> User:
    return User(id=42, email="collector@example.com", role="user")


async def fake_admin_user() -> User:
    return User(id=42, email="admin@example.com", role="admin")


class FakeJourneyService:
    def __init__(self) -> None:
        self.positions: list[JourneyPosition] = []

    async def start_journey(self, journey: Journey) -> Journey:
        return Journey(
            id=1,
            user_id=journey.user_id,
            status="started",
            profile=journey.profile,
            source_service=journey.source_service,
            source_client_id=journey.source_client_id,
            source_ride_id=journey.source_ride_id,
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

    async def add_positions_to_trace(
        self,
        *,
        journey_id: int,
        positions: list[JourneyPosition],
    ) -> list[JourneyPosition]:
        return await self.add_positions(
            journey_id=journey_id,
            user_id=0,
            positions=positions,
        )

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

    async def finish_trace(
        self,
        *,
        journey_id: int,
        finished_at: datetime | None = None,
    ) -> Journey:
        return Journey(
            id=journey_id,
            user_id=None,
            status="finished",
            profile="car",
            source_service="diddigo",
            source_client_id="diddigo-staging",
            source_ride_id="ride-123",
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
                source_service="diddigo" if user_id == 0 else None,
                source_client_id="diddigo-staging" if user_id == 0 else None,
                source_ride_id="ride-123" if user_id == 0 else None,
                start_location={"lng": -4.02, "lat": 5.33},
                end_location={"lng": -3.99, "lat": 5.34},
            ),
            positions=self.positions,
        )

    async def get_trace_detail_for_admin(self, *, trace_id: int) -> JourneyDetail:
        return await self.get_journey(journey_id=trace_id, user_id=0)

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

    async def analyze_journey(self, *, journey_id: int, user_id: int) -> JourneyAnalysis:
        return JourneyAnalysis(
            id=1,
            journey_id=journey_id,
            points_count=8,
            usable_points_count=8,
            quality_score=0.82,
            quality_label="good",
            actual_distance_m=1200,
            actual_duration_s=900,
            average_speed_kmh=4.8,
            phone_average_speed_kmh=5.1,
            moving_time_s=720,
            stopped_time_s=180,
            max_speed_kmh=18.2,
            gps_gap_count=1,
            suspicious_jump_count=0,
            planned_distance_m=1000,
            planned_duration_s=600,
            distance_delta_m=200,
            duration_delta_s=300,
            duration_ratio=1.5,
            detected_events=[
                {
                    "type": "duration_much_longer_than_planned",
                    "severity": 4,
                    "message": "Le trajet reel est nettement plus long que la duree OSRM prevue.",
                }
            ],
            recommendation="review_needed",
            created_at=datetime(2026, 7, 27, 10, 20, tzinfo=timezone.utc),
        )

    async def get_analysis(self, *, journey_id: int, user_id: int) -> JourneyAnalysis:
        return await self.analyze_journey(journey_id=journey_id, user_id=user_id)

    async def analyze_trace(self, *, journey_id: int) -> JourneyAnalysis:
        return await self.analyze_journey(journey_id=journey_id, user_id=0)

    async def list_insights(
        self,
        *,
        status: str | None = None,
        insight_type: str | None = None,
        severity_min: int | None = None,
        trace_id: int | None = None,
    ) -> list[MapTraceInsight]:
        insight = MapTraceInsight(
            id=3,
            journey_id=1,
            analysis_id=1,
            insight_type="duration_much_longer_than_planned",
            severity=4,
            confidence_score=0.74,
            message="Trace a revoir",
            status=status or "proposed",
        )
        if trace_id is not None and trace_id != insight.journey_id:
            return []
        if insight_type is not None and insight_type != insight.insight_type:
            return []
        if severity_min is not None and insight.severity < severity_min:
            return []
        return [insight]

    async def get_insight(self, *, insight_id: int) -> MapTraceInsight:
        return (await self.list_insights())[0]

    async def review_insight(
        self,
        *,
        insight_id: int,
        status: str,
        reviewed_by: int,
        review_note: str | None = None,
    ) -> MapTraceInsight:
        return MapTraceInsight(
            id=insight_id,
            journey_id=1,
            analysis_id=1,
            insight_type="duration_much_longer_than_planned",
            severity=4,
            confidence_score=0.74,
            message="Trace a revoir",
            status=status,
            reviewed_by=reviewed_by,
            review_note=review_note,
            reviewed_at=datetime(2026, 7, 27, 10, 30, tzinfo=timezone.utc),
        )


class ConvertFakeJourneyService(FakeJourneyService):
    async def get_insight(self, *, insight_id: int) -> MapTraceInsight:
        return MapTraceInsight(
            id=insight_id,
            journey_id=1,
            analysis_id=1,
            insight_type="duration_much_longer_than_planned",
            severity=4,
            confidence_score=0.74,
            message="Trace a revoir",
            geometry={
                "type": "LineString",
                "coordinates": [[-4.02, 5.33], [-4.01, 5.34], [-4.0, 5.35]],
            },
            status="validated",
            evidence_count=3,
            latest_evidence_trace_id=4,
        )


class QueueFakeJourneyService(FakeJourneyService):
    async def list_insights(
        self,
        *,
        status: str | None = None,
        insight_type: str | None = None,
        severity_min: int | None = None,
        trace_id: int | None = None,
    ) -> list[MapTraceInsight]:
        insights = [
            MapTraceInsight(
                id=1,
                journey_id=11,
                analysis_id=101,
                insight_type="slow_journey",
                severity=3,
                confidence_score=0.62,
                evidence_count=1,
                latest_evidence_trace_id=11,
                message="Signal faible",
                status="proposed",
            ),
            MapTraceInsight(
                id=2,
                journey_id=12,
                analysis_id=102,
                insight_type="possible_blocked_road",
                severity=5,
                confidence_score=0.78,
                evidence_count=3,
                latest_evidence_trace_id=15,
                message="Signal prioritaire",
                status="proposed",
            ),
            MapTraceInsight(
                id=3,
                journey_id=13,
                analysis_id=103,
                insight_type="possible_detour",
                severity=4,
                confidence_score=0.81,
                evidence_count=2,
                latest_evidence_trace_id=16,
                message="Pret pour conversion",
                status="validated",
            ),
        ]
        filtered = insights
        if status is not None:
            filtered = [insight for insight in filtered if insight.status == status]
        if insight_type is not None:
            filtered = [
                insight for insight in filtered if insight.insight_type == insight_type
            ]
        if severity_min is not None:
            filtered = [
                insight for insight in filtered if insight.severity >= severity_min
            ]
        if trace_id is not None:
            filtered = [insight for insight in filtered if insight.journey_id == trace_id]
        return filtered


class FinishedDiddiGoTraceService(FakeJourneyService):
    async def get_trace_detail_for_admin(self, *, trace_id: int) -> JourneyDetail:
        return JourneyDetail(
            journey=Journey(
                id=trace_id,
                user_id=None,
                status="finished",
                profile="car",
                source_service="diddigo",
                source_client_id="diddigo-staging",
                source_ride_id="ride-123",
                start_location={"lng": -4.02, "lat": 5.33},
                end_location={"lng": -3.99, "lat": 5.34},
                actual_distance_m=1200.5,
                actual_duration_s=900,
                started_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                finished_at=datetime(2026, 7, 27, 10, 15, tzinfo=timezone.utc),
            ),
            positions=[],
        )

    async def add_positions_to_trace(
        self,
        *,
        journey_id: int,
        positions: list[JourneyPosition],
    ) -> list[JourneyPosition]:
        raise JourneyNotStartedError("Journey is not accepting positions")


class UnfinishedDiddiGoTraceService(FakeJourneyService):
    async def analyze_trace(self, *, journey_id: int) -> JourneyAnalysis:
        raise JourneyNotFinishedError("Journey must be finished before analysis")


def test_journey_start_requires_authentication() -> None:
    response = client.post(
        "/api/v1/map-traces/start",
        json={
            "start": {"lng": -4.02, "lat": 5.33},
            "end": {"lng": -3.99, "lat": 5.34},
            "profile": "car",
        },
    )

    assert response.status_code == 401


def test_map_traces_are_the_public_openapi_contract() -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/map-traces/start" in paths
    assert "/api/v1/map-traces/{trace_id}/positions" in paths
    assert "/api/v1/journeys/start" not in paths


def test_journey_collection_workflow() -> None:
    service = FakeJourneyService()
    app.dependency_overrides[get_current_user] = fake_admin_user
    app.dependency_overrides[get_journey_service] = lambda: service

    start_response = client.post(
        "/api/v1/map-traces/start",
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
        "/api/v1/map-traces/1/positions",
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
    assert positions_response.json()[0]["trace_id"] == 1
    assert positions_response.json()[0]["location"] == {"lng": -4.019, "lat": 5.331}

    detail_response = client.get("/api/v1/map-traces/1")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["positions"]) == 1

    finish_response = client.post(
        "/api/v1/map-traces/1/finish",
        json={"finished_at": "2026-07-27T10:15:00Z"},
    )
    assert finish_response.status_code == 200
    assert finish_response.json()["status"] == "finished"
    assert finish_response.json()["actual_distance_m"] == 1200.5

    analysis_response = client.post("/api/v1/map-traces/1/analyze")
    assert analysis_response.status_code == 200
    assert analysis_response.json()["trace_id"] == 1
    assert "journey_id" not in analysis_response.json()
    assert analysis_response.json()["quality_label"] == "good"
    assert analysis_response.json()["recommendation"] == "review_needed"
    assert analysis_response.json()["moving_time_s"] == 720
    assert analysis_response.json()["stopped_time_s"] == 180
    assert analysis_response.json()["max_speed_kmh"] == 18.2
    assert analysis_response.json()["gps_gap_count"] == 1
    assert analysis_response.json()["suspicious_jump_count"] == 0

    get_analysis_response = client.get("/api/v1/map-traces/1/analysis")
    assert get_analysis_response.status_code == 200
    assert get_analysis_response.json()["average_speed_kmh"] == 4.8


def _service_headers(token: str = "service-secret") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Client-ID": "diddigo-staging",
    }


def test_diddigo_trace_start_requires_service_auth() -> None:
    response = client.post(
        "/api/v1/integrations/diddigo/map-traces/start",
        json={
            "source_ride_id": "ride-123",
            "start": {"lng": -4.02, "lat": 5.33},
            "end": {"lng": -3.99, "lat": 5.34},
            "profile": "car",
        },
    )

    assert response.status_code == 401


def test_diddigo_trace_workflow_uses_service_auth_and_ride_source(monkeypatch) -> None:
    token = "service-secret"
    monkeypatch.setattr(settings, "diddigo_service_client_id", "diddigo-staging")
    monkeypatch.setattr(
        settings,
        "diddigo_service_token_sha256",
        hashlib.sha256(token.encode("utf-8")).hexdigest(),
    )
    service = FakeJourneyService()
    app.dependency_overrides[get_journey_service] = lambda: service

    start_response = client.post(
        "/api/v1/integrations/diddigo/map-traces/start",
        headers=_service_headers(token),
        json={
            "source_ride_id": "ride-123",
            "start": {"lng": -4.02, "lat": 5.33},
            "end": {"lng": -3.99, "lat": 5.34},
            "profile": "car",
            "planned_distance_m": 1500,
            "planned_duration_s": 360,
        },
    )
    assert start_response.status_code == 201
    assert start_response.json()["user_id"] is None
    assert start_response.json()["source_service"] == "diddigo"
    assert start_response.json()["source_client_id"] == "diddigo-staging"
    assert start_response.json()["source_ride_id"] == "ride-123"

    positions_response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/positions",
        headers=_service_headers(token),
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
    assert positions_response.json()[0]["trace_id"] == 1

    finish_response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/finish",
        headers=_service_headers(token),
        json={"finished_at": "2026-07-27T10:15:00Z"},
    )
    assert finish_response.status_code == 200
    assert finish_response.json()["source_ride_id"] == "ride-123"

    retry_finish_response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/finish",
        headers=_service_headers(token),
        json={"finished_at": "2026-07-27T10:15:00Z"},
    )
    assert retry_finish_response.status_code == 200
    assert retry_finish_response.json()["status"] == "finished"

    analysis_response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/analyze",
        headers=_service_headers(token),
    )
    assert analysis_response.status_code == 200
    assert analysis_response.json()["trace_id"] == 1

    retry_analysis_response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/analyze",
        headers=_service_headers(token),
    )
    assert retry_analysis_response.status_code == 200
    assert retry_analysis_response.json()["trace_id"] == 1


def test_diddigo_positions_after_finish_return_business_conflict(monkeypatch) -> None:
    token = "service-secret"
    monkeypatch.setattr(settings, "diddigo_service_client_id", "diddigo-staging")
    monkeypatch.setattr(
        settings,
        "diddigo_service_token_sha256",
        hashlib.sha256(token.encode("utf-8")).hexdigest(),
    )
    app.dependency_overrides[get_journey_service] = lambda: FinishedDiddiGoTraceService()

    response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/positions",
        headers=_service_headers(token),
        json={
            "positions": [
                {
                    "lng": -4.019,
                    "lat": 5.331,
                    "recorded_at": "2026-07-27T10:16:00Z",
                }
            ]
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "trace_already_finished"


def test_diddigo_positions_with_invalid_latitude_return_validation_error(monkeypatch) -> None:
    token = "service-secret"
    monkeypatch.setattr(settings, "diddigo_service_client_id", "diddigo-staging")
    monkeypatch.setattr(
        settings,
        "diddigo_service_token_sha256",
        hashlib.sha256(token.encode("utf-8")).hexdigest(),
    )
    app.dependency_overrides[get_journey_service] = lambda: FakeJourneyService()

    response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/positions",
        headers=_service_headers(token),
        json={
            "positions": [
                {
                    "lng": -4.019,
                    "lat": 999,
                    "recorded_at": "2026-07-27T10:16:00Z",
                }
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["details"][0]["field"] == "positions[0].lat"


def test_diddigo_analyze_before_finish_returns_business_conflict(monkeypatch) -> None:
    token = "service-secret"
    monkeypatch.setattr(settings, "diddigo_service_client_id", "diddigo-staging")
    monkeypatch.setattr(
        settings,
        "diddigo_service_token_sha256",
        hashlib.sha256(token.encode("utf-8")).hexdigest(),
    )
    app.dependency_overrides[get_journey_service] = lambda: UnfinishedDiddiGoTraceService()

    response = client.post(
        "/api/v1/integrations/diddigo/map-traces/1/analyze",
        headers=_service_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "trace_not_finished"


def test_map_trace_insight_admin_workflow() -> None:
    service = FakeJourneyService()
    app.dependency_overrides[get_current_user] = fake_admin_user
    app.dependency_overrides[get_journey_service] = lambda: service

    list_response = client.get("/api/v1/map-trace-insights?status=proposed")
    assert list_response.status_code == 200
    assert list_response.json()[0]["trace_id"] == 1

    validate_response = client.post(
        "/api/v1/map-trace-insights/3/validate",
        json={"note": "Observation validee pour revue terrain"},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["status"] == "validated"
    assert validate_response.json()["reviewed_by"] == 42

    detail_response = client.get("/api/v1/map-trace-insights/3/detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["trace_id"] == 1
    assert detail_response.json()["trace"]["id"] == 1
    assert detail_response.json()["analysis"]["trace_id"] == 1


def test_map_trace_insights_can_be_sorted_for_admin_review() -> None:
    service = QueueFakeJourneyService()
    app.dependency_overrides[get_current_user] = fake_admin_user
    app.dependency_overrides[get_journey_service] = lambda: service

    response = client.get("/api/v1/map-trace-insights?sort=evidence&order=desc")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [2, 3, 1]


def test_map_trace_review_queue_prioritizes_strongest_proposed_insights() -> None:
    service = QueueFakeJourneyService()
    app.dependency_overrides[get_current_user] = fake_admin_user
    app.dependency_overrides[get_journey_service] = lambda: service

    response = client.get("/api/v1/map-trace-insights/review-queue")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [2, 1]
    assert body[0]["recommended_action"] == "review_priority"
    assert body[0]["review_priority_score"] > body[1]["review_priority_score"]


def test_map_trace_route_report_candidates_are_validated_and_strong_enough() -> None:
    service = QueueFakeJourneyService()
    app.dependency_overrides[get_current_user] = fake_admin_user
    app.dependency_overrides[get_journey_service] = lambda: service

    response = client.get("/api/v1/map-trace-insights/route-report-candidates")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [3]
    assert body[0]["conversion_ready"] is True
    assert body[0]["recommended_action"] == "convert_to_route_report"


def test_validated_map_trace_insight_can_convert_to_route_report(monkeypatch) -> None:
    class FakeRouteReportWorkflow:
        async def propose(self, report: RouteReport) -> RouteReport:
            return RouteReport(
                id=77,
                road_id=report.road_id,
                report_type=report.report_type,
                severity=report.severity,
                message=report.message,
                geometry=report.geometry,
                reported_by=report.reported_by,
                validation_status=report.validation_status,
                metadata=report.metadata,
            )

    service = ConvertFakeJourneyService()
    app.dependency_overrides[get_current_user] = fake_admin_user
    app.dependency_overrides[get_journey_service] = lambda: service
    monkeypatch.setattr(
        journeys_api,
        "_route_report_workflow",
        lambda session: FakeRouteReportWorkflow(),
    )

    response = client.post("/api/v1/map-trace-insights/3/convert-to-route-report")

    assert response.status_code == 200
    body = response.json()
    assert body["insight"]["trace_id"] == 1
    assert body["route_report"]["id"] == 77
    assert body["route_report"]["report_type"] == "degraded"
    assert body["route_report"]["validation_status"] == "proposed"
    assert body["route_report"]["extra_metadata"]["source"] == "map_trace_insight"
    assert body["route_report"]["extra_metadata"]["evidence_count"] == 3
    assert body["route_report"]["extra_metadata"]["latest_evidence_trace_id"] == 4


def test_journey_service_finish_is_idempotent_for_finished_trace() -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.finish_called = False

        async def create(self, journey: Journey) -> Journey:
            return journey

        async def add_positions(self, journey_id: int, positions: list[JourneyPosition]):
            return positions

        async def get_detail(self, journey_id: int, user_id: int):
            return JourneyDetail(
                journey=Journey(
                    id=journey_id,
                    user_id=user_id,
                    status="finished",
                    profile="car",
                    start_location={"lng": -4.02, "lat": 5.33},
                    end_location={"lng": -3.99, "lat": 5.34},
                    actual_distance_m=1200.5,
                    actual_duration_s=900,
                    started_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                    finished_at=datetime(2026, 7, 27, 10, 15, tzinfo=timezone.utc),
                ),
                positions=[],
            )

        async def get_detail_for_admin(self, journey_id: int):
            return await self.get_detail(journey_id, None)

        async def list_for_user(self, user_id: int):
            return []

        async def finish(
            self,
            journey_id: int,
            user_id: int | None,
            *,
            finished_at: datetime,
            actual_distance_m: float,
            actual_duration_s: int,
        ):
            self.finish_called = True
            return None

        async def save_analysis(self, journey_id: int, user_id: int, analysis: JourneyAnalysis):
            return analysis

        async def get_analysis(self, journey_id: int, user_id: int):
            return None

        async def replace_proposed_insights(
            self,
            analysis_id: int,
            insights: list[MapTraceInsight],
        ):
            return insights

        async def list_insights(
            self,
            status: str | None = None,
            insight_type: str | None = None,
            severity_min: int | None = None,
            trace_id: int | None = None,
        ):
            return []

        async def get_insight(self, insight_id: int):
            return None

        async def review_insight(
            self,
            insight_id: int,
            *,
            status: str,
            reviewed_by: int,
            review_note: str | None,
            reviewed_at: datetime,
        ):
            return None

    repository = FakeRepository()

    journey = asyncio.run(
        JourneyService(repository).finish_trace(
            journey_id=1,
            finished_at=datetime(2026, 7, 27, 10, 20, tzinfo=timezone.utc),
        )
    )

    assert journey.status == "finished"
    assert journey.finished_at == datetime(2026, 7, 27, 10, 15, tzinfo=timezone.utc)
    assert repository.finish_called is False


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

        async def get_detail_for_admin(self, journey_id: int):
            return await self.get_detail(journey_id, 42)

        async def list_for_user(self, user_id: int):
            return []

        async def save_analysis(self, journey_id: int, user_id: int, analysis: JourneyAnalysis):
            return analysis

        async def get_analysis(self, journey_id: int, user_id: int):
            return None

        async def replace_proposed_insights(
            self,
            analysis_id: int,
            insights: list[MapTraceInsight],
        ):
            return insights

        async def list_insights(
            self,
            status: str | None = None,
            insight_type: str | None = None,
            severity_min: int | None = None,
            trace_id: int | None = None,
        ):
            return []

        async def get_insight(self, insight_id: int):
            return None

        async def review_insight(
            self,
            insight_id: int,
            *,
            status: str,
            reviewed_by: int,
            review_note: str | None,
            reviewed_at: datetime,
        ):
            return None

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


def test_journey_service_analyzes_trace_speed_and_quality() -> None:
    class FakeRepository:
        async def create(self, journey: Journey) -> Journey:
            return journey

        async def add_positions(self, journey_id: int, positions: list[JourneyPosition]):
            return positions

        async def get_detail(self, journey_id: int, user_id: int):
            return JourneyDetail(
                journey=Journey(
                    id=journey_id,
                    user_id=user_id,
                    status="finished",
                    profile="car",
                    start_location={"lng": -4.02, "lat": 5.33},
                    end_location={"lng": -3.99, "lat": 5.34},
                    planned_distance_m=100,
                    planned_duration_s=30,
                    actual_duration_s=60,
                ),
                positions=[
                    JourneyPosition(
                        id=1,
                        journey_id=journey_id,
                        location={"lng": -4.0200, "lat": 5.3300},
                        accuracy_m=8,
                        speed_mps=2,
                        recorded_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=2,
                        journey_id=journey_id,
                        location={"lng": -4.0198, "lat": 5.3300},
                        accuracy_m=8,
                        speed_mps=3,
                        recorded_at=datetime(2026, 7, 27, 10, 0, 10, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=3,
                        journey_id=journey_id,
                        location={"lng": -4.0196, "lat": 5.3300},
                        accuracy_m=8,
                        speed_mps=4,
                        recorded_at=datetime(2026, 7, 27, 10, 0, 20, tzinfo=timezone.utc),
                    ),
                ],
            )

        async def get_detail_for_admin(self, journey_id: int):
            return await self.get_detail(journey_id, 42)

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
            return None

        async def save_analysis(self, journey_id: int, user_id: int, analysis: JourneyAnalysis):
            return JourneyAnalysis(**{**analysis.__dict__, "id": 9})

        async def get_analysis(self, journey_id: int, user_id: int):
            return None

        async def replace_proposed_insights(
            self,
            analysis_id: int,
            insights: list[MapTraceInsight],
        ):
            self.insights = insights
            return insights

        async def list_insights(
            self,
            status: str | None = None,
            insight_type: str | None = None,
            severity_min: int | None = None,
            trace_id: int | None = None,
        ):
            return []

        async def get_insight(self, insight_id: int):
            return None

        async def review_insight(
            self,
            insight_id: int,
            *,
            status: str,
            reviewed_by: int,
            review_note: str | None,
            reviewed_at: datetime,
        ):
            return None

    analysis = asyncio.run(
        JourneyService(FakeRepository()).analyze_journey(journey_id=1, user_id=42)
    )

    assert analysis.id == 9
    assert analysis.points_count == 3
    assert analysis.usable_points_count == 3
    assert analysis.actual_distance_m > 40
    assert analysis.average_speed_kmh > 2
    assert analysis.phone_average_speed_kmh == 10.8
    assert analysis.moving_time_s == 20
    assert analysis.stopped_time_s == 0
    assert analysis.max_speed_kmh > 0
    assert analysis.gps_gap_count == 0
    assert analysis.suspicious_jump_count == 0
    assert analysis.duration_ratio == 2
    assert analysis.recommendation == "review_needed"


def test_journey_service_detects_gps_gaps_and_suspicious_jumps() -> None:
    class FakeRepository:
        async def create(self, journey: Journey) -> Journey:
            return journey

        async def add_positions(self, journey_id: int, positions: list[JourneyPosition]):
            return positions

        async def get_detail(self, journey_id: int, user_id: int):
            return JourneyDetail(
                journey=Journey(
                    id=journey_id,
                    user_id=user_id,
                    status="finished",
                    profile="car",
                    start_location={"lng": -4.02, "lat": 5.33},
                    end_location={"lng": -3.99, "lat": 5.34},
                    actual_duration_s=410,
                ),
                positions=[
                    JourneyPosition(
                        id=1,
                        journey_id=journey_id,
                        location={"lng": -4.0200, "lat": 5.3300},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=2,
                        journey_id=journey_id,
                        location={"lng": -3.9000, "lat": 5.3300},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 0, 10, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=3,
                        journey_id=journey_id,
                        location={"lng": -3.9001, "lat": 5.3300},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 6, 50, tzinfo=timezone.utc),
                    ),
                ],
            )

        async def get_detail_for_admin(self, journey_id: int):
            return await self.get_detail(journey_id, 42)

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
            return None

        async def save_analysis(self, journey_id: int, user_id: int, analysis: JourneyAnalysis):
            return analysis

        async def get_analysis(self, journey_id: int, user_id: int):
            return None

        async def replace_proposed_insights(
            self,
            analysis_id: int,
            insights: list[MapTraceInsight],
        ):
            return insights

        async def list_insights(
            self,
            status: str | None = None,
            insight_type: str | None = None,
            severity_min: int | None = None,
            trace_id: int | None = None,
        ):
            return []

        async def get_insight(self, insight_id: int):
            return None

        async def review_insight(
            self,
            insight_id: int,
            *,
            status: str,
            reviewed_by: int,
            review_note: str | None,
            reviewed_at: datetime,
        ):
            return None

    analysis = asyncio.run(
        JourneyService(FakeRepository()).analyze_journey(journey_id=1, user_id=42)
    )

    event_types = {event["type"] for event in analysis.detected_events}

    assert analysis.gps_gap_count == 1
    assert analysis.suspicious_jump_count == 1
    assert "gps_time_gap" in event_types
    assert "suspicious_gps_jump" in event_types
    assert "possible_slow_segment" in event_types


def test_journey_service_detects_blocked_road_and_detour_candidates() -> None:
    class FakeRepository:
        async def create(self, journey: Journey) -> Journey:
            return journey

        async def add_positions(self, journey_id: int, positions: list[JourneyPosition]):
            return positions

        async def get_detail(self, journey_id: int, user_id: int):
            return JourneyDetail(
                journey=Journey(
                    id=journey_id,
                    user_id=user_id,
                    status="finished",
                    profile="car",
                    start_location={"lng": -4.02, "lat": 5.33},
                    end_location={"lng": -4.014, "lat": 5.33},
                    planned_distance_m=100,
                    planned_duration_s=100,
                    actual_duration_s=600,
                ),
                positions=[
                    JourneyPosition(
                        id=1,
                        journey_id=journey_id,
                        location={"lng": -4.020, "lat": 5.330},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=2,
                        journey_id=journey_id,
                        location={"lng": -4.017, "lat": 5.330},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 5, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=3,
                        journey_id=journey_id,
                        location={"lng": -4.014, "lat": 5.330},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 10, tzinfo=timezone.utc),
                    ),
                ],
            )

        async def get_detail_for_admin(self, journey_id: int):
            return await self.get_detail(journey_id, 42)

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
            return None

        async def save_analysis(self, journey_id: int, user_id: int, analysis: JourneyAnalysis):
            return analysis

        async def get_analysis(self, journey_id: int, user_id: int):
            return None

        async def replace_proposed_insights(
            self,
            analysis_id: int,
            insights: list[MapTraceInsight],
        ):
            return insights

        async def list_insights(
            self,
            status: str | None = None,
            insight_type: str | None = None,
            severity_min: int | None = None,
            trace_id: int | None = None,
        ):
            return []

        async def get_insight(self, insight_id: int):
            return None

        async def review_insight(
            self,
            insight_id: int,
            *,
            status: str,
            reviewed_by: int,
            review_note: str | None,
            reviewed_at: datetime,
        ):
            return None

    analysis = asyncio.run(
        JourneyService(FakeRepository()).analyze_journey(journey_id=1, user_id=42)
    )

    event_types = {event["type"] for event in analysis.detected_events}

    assert analysis.duration_ratio == 6
    assert analysis.actual_distance_m > 500
    assert "possible_slow_segment" in event_types
    assert "possible_blocked_road" in event_types
    assert "possible_detour" in event_types


def test_map_trace_insights_get_stable_duplicate_keys() -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.insights: list[MapTraceInsight] = []

        async def create(self, journey: Journey) -> Journey:
            return journey

        async def add_positions(self, journey_id: int, positions: list[JourneyPosition]):
            return positions

        async def get_detail(self, journey_id: int, user_id: int):
            return JourneyDetail(
                journey=Journey(
                    id=journey_id,
                    user_id=user_id,
                    status="finished",
                    profile="car",
                    start_location={"lng": -4.02, "lat": 5.33},
                    end_location={"lng": -4.014, "lat": 5.33},
                    planned_distance_m=100,
                    planned_duration_s=100,
                    planned_route_geometry={
                        "type": "LineString",
                        "coordinates": [
                            [-4.0201, 5.3301],
                            [-4.0174, 5.3303],
                            [-4.0148, 5.3305],
                        ],
                    },
                    actual_duration_s=600,
                ),
                positions=[
                    JourneyPosition(
                        id=1,
                        journey_id=journey_id,
                        location={"lng": -4.020, "lat": 5.330},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=2,
                        journey_id=journey_id,
                        location={"lng": -4.017, "lat": 5.330},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 5, tzinfo=timezone.utc),
                    ),
                    JourneyPosition(
                        id=3,
                        journey_id=journey_id,
                        location={"lng": -4.014, "lat": 5.330},
                        accuracy_m=8,
                        recorded_at=datetime(2026, 7, 27, 10, 10, tzinfo=timezone.utc),
                    ),
                ],
            )

        async def get_detail_for_admin(self, journey_id: int):
            return await self.get_detail(journey_id, 42)

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
            return None

        async def save_analysis(self, journey_id: int, user_id: int, analysis: JourneyAnalysis):
            return JourneyAnalysis(**{**analysis.__dict__, "id": 9})

        async def get_analysis(self, journey_id: int, user_id: int):
            return None

        async def replace_proposed_insights(
            self,
            analysis_id: int,
            insights: list[MapTraceInsight],
        ):
            self.insights = insights
            return insights

        async def list_insights(
            self,
            status: str | None = None,
            insight_type: str | None = None,
            severity_min: int | None = None,
            trace_id: int | None = None,
        ):
            return []

        async def get_insight(self, insight_id: int):
            return None

        async def review_insight(
            self,
            insight_id: int,
            *,
            status: str,
            reviewed_by: int,
            review_note: str | None,
            reviewed_at: datetime,
        ):
            return None

    repository = FakeRepository()

    asyncio.run(JourneyService(repository).analyze_journey(journey_id=1, user_id=42))

    keys = {
        insight.insight_type: insight.duplicate_key
        for insight in repository.insights
        if insight.duplicate_key is not None
    }

    assert keys["possible_slow_segment"] == "possible_slow_segment:-4.017:5.330"
    assert keys["possible_blocked_road"] == "possible_blocked_road:-4.017:5.330"
    assert keys["possible_detour"] == "possible_detour:-4.017:5.330"


def test_repository_filters_duplicate_active_insights() -> None:
    class ExistingInsight:
        duplicate_key = "possible_slow_segment:-4.017:5.330"
        journey_id = 99
        evidence_count = 2
        latest_evidence_trace_id = 88
        severity = 2
        confidence_score = 0.4

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [existing]

    class FakeSession:
        async def execute(self, statement):
            return FakeResult()

    existing = ExistingInsight()
    repository = SQLAlchemyJourneyRepository(FakeSession())  # type: ignore[arg-type]

    filtered = asyncio.run(
        repository._filter_duplicate_insights(
            9,
            [
                MapTraceInsight(
                    journey_id=1,
                    analysis_id=9,
                    insight_type="possible_slow_segment",
                    severity=3,
                    confidence_score=0.7,
                    message="Duplicate",
                    duplicate_key="possible_slow_segment:-4.017:5.330",
                ),
                MapTraceInsight(
                    journey_id=1,
                    analysis_id=9,
                    insight_type="possible_detour",
                    severity=4,
                    confidence_score=0.8,
                    message="New candidate",
                    duplicate_key="possible_detour:-4.017:5.330",
                ),
                MapTraceInsight(
                    journey_id=1,
                    analysis_id=9,
                    insight_type="possible_detour",
                    severity=4,
                    confidence_score=0.8,
                    message="Same batch duplicate",
                    duplicate_key="possible_detour:-4.017:5.330",
                ),
            ],
        )
    )

    assert [insight.insight_type for insight in filtered] == ["possible_detour"]
    assert existing.evidence_count == 3
    assert existing.latest_evidence_trace_id == 1
    assert existing.severity == 3
    assert existing.confidence_score == 0.7


def test_repository_does_not_count_same_trace_duplicate_as_new_evidence() -> None:
    class ExistingInsight:
        duplicate_key = "possible_slow_segment:-4.017:5.330"
        journey_id = 1
        evidence_count = 2
        latest_evidence_trace_id = 1
        severity = 2
        confidence_score = 0.4

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [existing]

    class FakeSession:
        async def execute(self, statement):
            return FakeResult()

    existing = ExistingInsight()
    repository = SQLAlchemyJourneyRepository(FakeSession())  # type: ignore[arg-type]

    filtered = asyncio.run(
        repository._filter_duplicate_insights(
            9,
            [
                MapTraceInsight(
                    journey_id=1,
                    analysis_id=9,
                    insight_type="possible_slow_segment",
                    severity=5,
                    confidence_score=0.9,
                    message="Same trace duplicate",
                    duplicate_key="possible_slow_segment:-4.017:5.330",
                )
            ],
        )
    )

    assert filtered == []
    assert existing.evidence_count == 2
    assert existing.latest_evidence_trace_id == 1
    assert existing.severity == 2
    assert existing.confidence_score == 0.4
