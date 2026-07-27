from pathlib import Path

from app.modules.journeys.infrastructure.persistence.models import (
    JourneyAnalysisORM,
    JourneyORM,
    JourneyPositionORM,
    MapTraceInsightORM,
)
from app.modules.local_enrichment.infrastructure.persistence.models import (
    RouteReportHistoryORM,
    RouteReportORM,
)
from app.modules.map_data.infrastructure.persistence.models import (
    PlaceHistoryORM,
    PlaceORM,
    RoadHistoryORM,
    RoadORM,
)
from app.modules.users.infrastructure.persistence.models import UserORM
from app.shared.infrastructure.persistence.base import Base


APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def test_module_owned_models_share_one_metadata_registry() -> None:
    assert set(Base.metadata.tables) == {
        "journey_positions",
        "journey_analyses",
        "journeys",
        "map_trace_insights",
        "place_history",
        "places",
        "road_history",
        "roads",
        "route_report_history",
        "route_reports",
        "users",
    }


def test_orm_models_are_owned_by_their_business_modules() -> None:
    map_data_models = (RoadORM, PlaceORM, RoadHistoryORM, PlaceHistoryORM)
    assert all(model.__module__.startswith("app.modules.map_data.") for model in map_data_models)
    assert RouteReportORM.__module__.startswith("app.modules.local_enrichment.")
    assert RouteReportHistoryORM.__module__.startswith("app.modules.local_enrichment.")
    assert UserORM.__module__.startswith("app.modules.users.")
    assert JourneyORM.__module__.startswith("app.modules.journeys.")
    assert JourneyPositionORM.__module__.startswith("app.modules.journeys.")
    assert JourneyAnalysisORM.__module__.startswith("app.modules.journeys.")
    assert MapTraceInsightORM.__module__.startswith("app.modules.journeys.")


def test_legacy_horizontal_architecture_is_absent() -> None:
    legacy_directories = ("application", "domain", "infrastructure", "presentation")
    assert all(not (APP_ROOT / directory).exists() for directory in legacy_directories)


def test_canonical_code_does_not_import_legacy_packages() -> None:
    forbidden_imports = (
        "app.application",
        "app.domain",
        "app.infrastructure",
        "app.presentation",
    )
    canonical_roots = (APP_ROOT / "bootstrap", APP_ROOT / "modules", APP_ROOT / "shared")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for root in canonical_roots
        for path in root.rglob("*.py")
    )
    assert not any(forbidden in source for forbidden in forbidden_imports)
