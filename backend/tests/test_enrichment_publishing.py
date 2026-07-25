import asyncio
from types import SimpleNamespace

from app.modules.routing.infrastructure.enrichment.postgis_repository import (
    SQLAlchemyRouteEnrichmentRepository,
)
from app.shared.domain.vehicle import build_vehicle_context


class EmptyScalarResult:
    def __init__(self, items: list | None = None) -> None:
        self.items = items or []

    def all(self) -> list:
        return self.items


class EmptyResult:
    def __init__(self, items: list | None = None) -> None:
        self.items = items or []

    def scalars(self) -> EmptyScalarResult:
        return EmptyScalarResult(self.items)


class RecordingSession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement) -> EmptyResult:
        self.statements.append(str(statement))
        return EmptyResult()


class SequenceSession:
    def __init__(self, results: list[list]) -> None:
        self.results = list(results)

    async def execute(self, statement) -> EmptyResult:
        return EmptyResult(self.results.pop(0))


def test_enrichment_queries_only_select_validated_data() -> None:
    session = RecordingSession()
    repository = SQLAlchemyRouteEnrichmentRepository(session)

    detail = asyncio.run(
        repository.build_detail_from_route_geometry(
            {
                "type": "LineString",
                "coordinates": [[-4.02, 5.33], [-3.99, 5.34]],
            }
        )
    )

    assert detail.troncons == []
    assert detail.reports == []
    assert len(session.statements) == 2
    assert "roads.validation_status" in session.statements[0]
    assert "route_reports.validation_status" in session.statements[1]
    assert "ST_DWithin" in session.statements[0]
    assert "ST_DWithin" in session.statements[1]


def test_truck_constraints_are_detected_from_validated_road_data() -> None:
    road = SimpleNamespace(
        id=1,
        name="Route locale",
        surface_state="good",
        seasonal_practicability="all_year",
        is_blocked=False,
        point_controle="none",
        width_usable_m=2.7,
        tonnage_max_reel_t=10.0,
        allowed_vehicle_profiles=["car", "motorcycle"],
        securite_nuit=4,
        type_flux="free",
        validation_status="validated",
    )
    session = SequenceSession([[road], [], []])
    repository = SQLAlchemyRouteEnrichmentRepository(session)

    detail = asyncio.run(
        repository.build_detail_from_route_geometry(
            {
                "type": "LineString",
                "coordinates": [[-4.02, 5.33], [-3.99, 5.34]],
            },
            build_vehicle_context("truck", width_m=2.6, weight_t=19),
        )
    )

    assert detail.factors.vehicle_forbidden is True
    assert detail.factors.vehicle_overweight is True
    assert detail.factors.vehicle_too_wide is True
    assert detail.factors.narrow_width is True
    assert detail.troncons[0].allowed_vehicle_profiles == ["car", "motorcycle"]
