from fastapi.testclient import TestClient

from app.main import app
from app.modules.routing.application.use_cases.calculate_route import CalculateRoute
from app.modules.map_data.presentation import places_api as places_module
from app.modules.map_data.presentation import roads_api as roads_module
from app.modules.local_enrichment.presentation import api as route_reports_module
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user


client = TestClient(app)


class FakeRoad:
    def __init__(
        self,
        road_id: int,
        name: str,
        surface_state: str,
        seasonal_practicability: str,
        width_usable_m: float | None,
        tonnage_max_reel_t: float | None,
        allowed_vehicle_profiles: list[str],
        is_blocked: bool,
        extra_metadata: dict,
        geometry: dict | None = None,
    ) -> None:
        self.id = road_id
        self.name = name
        self.geometry = geometry
        self.surface_state = surface_state
        self.seasonal_practicability = seasonal_practicability
        self.width_usable_m = width_usable_m
        self.tonnage_max_reel_t = tonnage_max_reel_t
        self.allowed_vehicle_profiles = allowed_vehicle_profiles
        self.is_blocked = is_blocked
        self.validation_status = "proposed"
        self.extra_metadata = extra_metadata


class FakePlace:
    def __init__(
        self,
        place_id: int,
        name: str,
        category: str,
        aliases: list[str],
        description: str | None,
        verified: bool,
        extra_metadata: dict,
        location: dict | None = None,
    ) -> None:
        self.id = place_id
        self.name = name
        self.category = category
        self.location = location
        self.aliases = aliases
        self.description = description
        self.verified = verified
        self.validation_status = "proposed"
        self.extra_metadata = extra_metadata


class FakeRouteReport:
    def __init__(
        self,
        report_id: int,
        road_id: int | None,
        report_type: str,
        severity: int,
        message: str,
        reported_by: str | None,
        extra_metadata: dict,
        geometry: dict | None = None,
    ) -> None:
        self.id = report_id
        self.road_id = road_id
        self.report_type = report_type
        self.severity = severity
        self.message = message
        self.geometry = geometry
        self.reported_by = reported_by
        self.validation_status = "proposed"
        self.reviewed_by = None
        self.reviewed_at = None
        self.metadata = extra_metadata
        self.reported_at = None
        self.created_at = None
        self.updated_at = None


class FakeRouteReportHistory:
    def __init__(
        self,
        history_id: int,
        report_id: int,
        action: str,
        old_value: dict | None,
        new_value: dict | None,
        changed_by: str | None,
        note: str | None,
    ) -> None:
        self.id = history_id
        self.route_report_id = report_id
        self.action = action
        self.old_value = old_value
        self.new_value = new_value
        self.changed_by = changed_by
        self.note = note
        self.created_at = None


class FakeMapHistory:
    def __init__(
        self,
        history_id: int,
        item_id: int,
        item_type: str,
        action: str,
        old_value: dict | None,
        new_value: dict | None,
        changed_by: str | None,
        note: str | None,
    ) -> None:
        self.id = history_id
        setattr(self, f"{item_type}_id", item_id)
        self.action = action
        self.field_name = "multiple"
        self.old_value = old_value
        self.new_value = new_value
        self.changed_by = changed_by
        self.note = note
        self.created_at = None


class FakeRoadRepository:
    store: list[FakeRoad] = []
    history: list[FakeMapHistory] = []
    next_id = 1

    def __init__(self, session) -> None:
        self.session = session

    async def create(self, road, changed_by: str | None = None):
        item = FakeRoad(
            road_id=self.__class__.next_id,
            name=road.name,
            surface_state=road.surface_state,
            seasonal_practicability=road.seasonal_practicability,
            width_usable_m=road.width_usable_m,
            tonnage_max_reel_t=road.tonnage_max_reel_t,
            allowed_vehicle_profiles=road.allowed_vehicle_profiles,
            is_blocked=road.is_blocked,
            extra_metadata=road.metadata,
            geometry=road.geometry,
        )
        self.__class__.store.append(item)
        self.__class__.next_id += 1
        return item

    async def list_all(self):
        return list(self.__class__.store)

    async def get_by_id(self, road_id: int):
        for item in self.__class__.store:
            if item.id == road_id:
                return item
        return None

    async def update(
        self,
        road_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ):
        item = await self.get_by_id(road_id)
        if item is None:
            return None
        old_values = {}
        for field, value in changes.items():
            attribute = "extra_metadata" if field == "extra_metadata" else field
            old_values[field] = getattr(item, attribute, None)
            setattr(item, attribute, value)
        self.__class__.history.append(
            FakeMapHistory(
                history_id=len(self.__class__.history) + 1,
                item_id=road_id,
                item_type="road",
                action="update",
                old_value=old_values,
                new_value=changes,
                changed_by=changed_by,
                note=note,
            )
        )
        return item

    async def set_validation_status(self, road_id: int, status: str, **kwargs):
        item = await self.get_by_id(road_id)
        if item is None:
            return None
        item.validation_status = status
        return item

    async def list_history(self, road_id: int):
        return [
            item
            for item in reversed(self.__class__.history)
            if item.road_id == road_id
        ]

    async def add_history_entry(self, *args, **kwargs):
        return None


class FakePlaceRepository:
    store: list[FakePlace] = []
    history: list[FakeMapHistory] = []
    next_id = 1

    def __init__(self, session) -> None:
        self.session = session

    async def create(self, place, changed_by: str | None = None):
        item = FakePlace(
            place_id=self.__class__.next_id,
            name=place.name,
            category=place.category,
            aliases=place.aliases,
            description=place.description,
            verified=place.verified,
            extra_metadata=place.metadata,
            location=place.location,
        )
        self.__class__.store.append(item)
        self.__class__.next_id += 1
        return item

    async def list_all(self):
        return list(self.__class__.store)

    async def get_by_id(self, place_id: int):
        for item in self.__class__.store:
            if item.id == place_id:
                return item
        return None

    async def update(
        self,
        place_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ):
        item = await self.get_by_id(place_id)
        if item is None:
            return None
        old_values = {}
        for field, value in changes.items():
            attribute = "extra_metadata" if field == "extra_metadata" else field
            old_values[field] = getattr(item, attribute, None)
            setattr(item, attribute, value)
        self.__class__.history.append(
            FakeMapHistory(
                history_id=len(self.__class__.history) + 1,
                item_id=place_id,
                item_type="place",
                action="update",
                old_value=old_values,
                new_value=changes,
                changed_by=changed_by,
                note=note,
            )
        )
        return item

    async def set_validation_status(self, place_id: int, status: str, **kwargs):
        item = await self.get_by_id(place_id)
        if item is None:
            return None
        item.validation_status = status
        item.verified = status == "validated"
        return item

    async def list_history(self, place_id: int):
        return [
            item
            for item in reversed(self.__class__.history)
            if item.place_id == place_id
        ]


class FakeRouteReportRepository:
    store: list[FakeRouteReport] = []
    history: list[FakeRouteReportHistory] = []
    next_id = 1

    def __init__(self, session) -> None:
        self.session = session

    async def create(self, report):
        item = FakeRouteReport(
            report_id=self.__class__.next_id,
            road_id=report.road_id,
            report_type=report.report_type,
            severity=report.severity,
            message=report.message,
            reported_by=report.reported_by,
            extra_metadata=report.metadata,
            geometry=report.geometry,
        )
        self.__class__.store.append(item)
        self.__class__.history.append(
            FakeRouteReportHistory(
                history_id=len(self.__class__.history) + 1,
                report_id=item.id,
                action="propose",
                old_value=None,
                new_value={"validation_status": "proposed"},
                changed_by=item.reported_by,
                note="Route report proposed",
            )
        )
        self.__class__.next_id += 1
        return item

    async def list_all(self, validation_status: str | None = None):
        if validation_status is None:
            return list(self.__class__.store)
        return [
            item
            for item in self.__class__.store
            if item.validation_status == validation_status
        ]

    async def get_by_id(self, report_id: int):
        for item in self.__class__.store:
            if item.id == report_id:
                return item
        return None

    async def update(
        self,
        report_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ):
        item = await self.get_by_id(report_id)
        if item is None:
            return None
        old_values = {}
        for field, value in changes.items():
            attribute = "metadata" if field == "extra_metadata" else field
            old_values[field] = getattr(item, attribute, None)
            setattr(item, attribute, value)
        self.__class__.history.append(
            FakeRouteReportHistory(
                history_id=len(self.__class__.history) + 1,
                report_id=report_id,
                action="update",
                old_value=old_values,
                new_value=changes,
                changed_by=changed_by,
                note=note,
            )
        )
        return item

    async def set_validation_status(
        self,
        report_id: int,
        status: str,
        reviewed_by: str | None = None,
        note: str | None = None,
    ):
        item = await self.get_by_id(report_id)
        if item is None:
            return None
        old_status = item.validation_status
        item.validation_status = status
        item.reviewed_by = reviewed_by
        self.__class__.history.append(
            FakeRouteReportHistory(
                history_id=len(self.__class__.history) + 1,
                report_id=report_id,
                action="validate" if status == "validated" else "reject",
                old_value={"validation_status": old_status},
                new_value={"validation_status": status},
                changed_by=reviewed_by,
                note=note,
            )
        )
        return item

    async def list_history(self, report_id: int):
        return [
            item
            for item in reversed(self.__class__.history)
            if item.route_report_id == report_id
        ]


class FakeRouteEnrichmentRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def build_factors_from_route_geometry(self, route_geometry: dict, vehicle=None):
        from app.modules.routing.application.services.route_scoring import RouteLocalFactors

        return RouteLocalFactors(blocked=False, degraded=True, toll_present=True, seasonal_risk_multiplier=1.1)

    async def build_detail_from_route_geometry(self, route_geometry: dict, vehicle=None):
        from app.modules.routing.application.services.route_enrichment_models import (
            EnrichmentReport,
            EnrichmentTroncon,
            RouteEnrichmentDetail,
        )
        from app.modules.routing.application.services.route_scoring import RouteLocalFactors

        return RouteEnrichmentDetail(
            factors=RouteLocalFactors(
                blocked=False,
                degraded=True,
                toll_present=True,
                requested_vehicle_profile=vehicle.profile if vehicle else "car",
                vehicle_width_m=vehicle.width_m if vehicle else 1.9,
                vehicle_weight_t=vehicle.weight_t if vehicle else 2.5,
                seasonal_risk_multiplier=1.1,
            ),
            troncons=[
                EnrichmentTroncon(
                    road_id=1,
                    road_name="Route test",
                    validation_status="validated",
                    surface_state="degraded",
                    seasonal_practicability="all_year",
                    is_blocked=False,
                    point_controle=None,
                    width_usable_m=5.0,
                    tonnage_max_reel_t=10.0,
                    allowed_vehicle_profiles=["car", "motorcycle"],
                    securite_nuit=3,
                    type_flux="toll",
                )
            ],
            reports=[
                EnrichmentReport(
                    id=1,
                    road_id=1,
                    report_type="degraded",
                    severity=3,
                    message="Etat degrade",
                )
            ],
        )


def override_session():
    return object()


async def override_current_user() -> User:
    return User(
        id=1,
        email="admin@abidjanmaps.local",
        role="admin",
    )


def setup_function() -> None:
    FakeRoadRepository.store = []
    FakeRoadRepository.history = []
    FakeRoadRepository.next_id = 1
    FakePlaceRepository.store = []
    FakePlaceRepository.history = []
    FakePlaceRepository.next_id = 1
    FakeRouteReportRepository.store = []
    FakeRouteReportRepository.history = []
    FakeRouteReportRepository.next_id = 1
    app.dependency_overrides.clear()
    app.dependency_overrides[roads_module.get_async_session] = override_session
    app.dependency_overrides[places_module.get_async_session] = override_session
    app.dependency_overrides[route_reports_module.get_async_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    roads_module.SQLAlchemyRoadRepository = FakeRoadRepository
    places_module.SQLAlchemyPlaceRepository = FakePlaceRepository
    route_reports_module.SQLAlchemyRouteReportRepository = FakeRouteReportRepository
    route_reports_module.SQLAlchemyRoadRepository = FakeRoadRepository
    from app.modules.routing.presentation import proposal_api as route_proposals_module

    route_proposals_module.SQLAlchemyRouteEnrichmentRepository = FakeRouteEnrichmentRepository


def test_create_and_get_road() -> None:
    response = client.post(
        "/api/v1/roads",
        json={
            "name": "Route de Cocody",
            "geometry": {"type": "LineString", "coordinates": [[-4.02, 5.33], [-3.99, 5.34]]},
            "surface_state": "good",
            "seasonal_practicability": "all_year",
            "width_usable_m": 7.5,
            "allowed_vehicle_profiles": ["voiture", "moto"],
            "is_blocked": False,
            "extra_metadata": {"source": "field"},
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] == 1

    response = client.get("/api/v1/roads/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Route de Cocody"
    assert response.json()["geometry"] == {
        "type": "LineString",
        "coordinates": [[-4.02, 5.33], [-3.99, 5.34]],
    }
    assert response.json()["allowed_vehicle_profiles"] == ["car", "motorcycle"]


def test_list_places() -> None:
    client.post(
        "/api/v1/places",
        json={
            "name": "Carrefour Anador",
            "category": "landmark",
            "location": {"lng": -4.0, "lat": 5.3},
            "aliases": ["Anador"],
            "description": "Repere local",
            "verified": True,
            "extra_metadata": {"district": "Yopougon"},
        },
    )
    response = client.get("/api/v1/places")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Carrefour Anador"
    assert response.json()[0]["location"] == {"lng": -4.0, "lat": 5.3}


def test_create_and_get_route_report() -> None:
    response = client.post(
        "/api/v1/route-reports",
        json={
            "road_id": 1,
            "report_type": "flood",
            "severity": 4,
            "message": "Route inondee",
            "geometry": {"lng": -4.01, "lat": 5.31},
            "reported_by": "spoofed-client",
            "extra_metadata": {"photo": "yes"},
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["validation_status"] == "proposed"
    assert response.json()["reported_by"] == "admin@abidjanmaps.local"

    response = client.get("/api/v1/route-reports/1")
    assert response.status_code == 200
    assert response.json()["report_type"] == "flood"
    assert response.json()["geometry"] == {"lng": -4.01, "lat": 5.31}


def test_route_report_must_be_reviewed_before_publication() -> None:
    create_response = client.post(
        "/api/v1/route-reports",
        json={
            "road_id": 1,
            "report_type": "blocked",
            "severity": 5,
            "message": "Route barree",
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["validation_status"] == "proposed"

    proposed_response = client.get("/api/v1/route-reports?status=proposed")
    assert proposed_response.status_code == 200
    assert len(proposed_response.json()) == 1

    validate_response = client.post(
        "/api/v1/route-reports/1/validate",
        json={"note": "Photo verifiee"},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["validation_status"] == "validated"
    assert validate_response.json()["reviewed_by"] == "admin@abidjanmaps.local"

    assert client.get("/api/v1/route-reports?status=proposed").json() == []
    validated = client.get("/api/v1/route-reports?status=validated").json()
    assert len(validated) == 1

    history_response = client.get("/api/v1/route-reports/1/history")
    assert history_response.status_code == 200
    assert [item["action"] for item in history_response.json()] == [
        "validate",
        "propose",
    ]


def test_public_creation_cannot_self_validate_a_place() -> None:
    response = client.post(
        "/api/v1/places",
        json={
            "name": "Lieu propose",
            "category": "landmark",
            "location": {"lng": -4.0, "lat": 5.3},
            "validation_status": "validated",
        },
    )
    assert response.status_code == 201
    assert response.json()["validation_status"] == "proposed"
    assert response.json()["verified"] is False


def test_updating_validated_road_returns_it_to_proposed() -> None:
    create_response = client.post(
        "/api/v1/roads",
        json={
            "name": "Boulevard test",
            "geometry": {
                "type": "LineString",
                "coordinates": [[-4.02, 5.33], [-3.99, 5.34]],
            },
            "surface_state": "good",
            "seasonal_practicability": "all_year",
        },
    )
    assert create_response.status_code == 201
    assert client.post("/api/v1/roads/1/validate").json()["validation_status"] == "validated"

    patch_response = client.patch(
        "/api/v1/roads/1",
        json={
            "surface_state": "damaged",
            "changed_by": "spoofed-client",
            "note": "Verification terrain",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["surface_state"] == "damaged"
    assert patch_response.json()["validation_status"] == "proposed"

    history = client.get("/api/v1/roads/1/history").json()
    assert history[0]["action"] == "update"
    assert history[0]["old_value"]["validation_status"] == "validated"
    assert history[0]["new_value"]["validation_status"] == "proposed"
    assert history[0]["changed_by"] == "admin@abidjanmaps.local"


def test_updating_validated_place_clears_verified_flag() -> None:
    create_response = client.post(
        "/api/v1/places",
        json={
            "name": "Ancien nom",
            "category": "landmark",
            "location": {"lng": -4.0, "lat": 5.3},
        },
    )
    assert create_response.status_code == 201
    validated = client.post("/api/v1/places/1/validate").json()
    assert validated["verified"] is True

    patch_response = client.patch(
        "/api/v1/places/1",
        json={"name": "Nouveau nom"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Nouveau nom"
    assert patch_response.json()["validation_status"] == "proposed"
    assert patch_response.json()["verified"] is False


def test_updating_validated_report_requires_new_review() -> None:
    client.post(
        "/api/v1/route-reports",
        json={
            "report_type": "flood",
            "severity": 3,
            "message": "Eau sur la route",
        },
    )
    client.post(
        "/api/v1/route-reports/1/validate",
        json={},
    )

    patch_response = client.patch(
        "/api/v1/route-reports/1",
        json={
            "severity": 5,
            "note": "Niveau d'eau en hausse",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["severity"] == 5
    assert patch_response.json()["validation_status"] == "proposed"
    assert patch_response.json()["reviewed_by"] is None

    history = client.get("/api/v1/route-reports/1/history").json()
    assert [item["action"] for item in history] == [
        "update",
        "validate",
        "propose",
    ]


def test_patch_rejects_payload_without_business_change() -> None:
    response = client.patch(
        "/api/v1/roads/999",
        json={"note": "No business change"},
    )
    assert response.status_code == 400


def test_route_proposals_detail_includes_enrichment() -> None:
    from app.modules.routing.presentation import proposal_api as route_proposals_module
    from app.modules.routing.presentation import route_api as route_module

    class FakeRoutingEngine:
        def calculate_routes(self, start, end, request_id=None, max_alternatives=3):
            from app.modules.routing.domain.entities.route import Route

            return [
                Route(
                    geometry={"type": "LineString", "coordinates": [[-4.0, 5.3], [-3.9, 5.31]]},
                    distance_m=1000,
                    duration_s=200,
                )
            ]

    class FakePricingService:
        def calculate_price(self, distance_m: int, duration_s: int, profile: str):
            from app.modules.routing.domain.entities.price import Price

            return Price(amount=900)

    class FakeCoverageService:
        def is_covered(self, coordinate):
            return True

    def override_use_case():
        return CalculateRoute(
            routing_engine=FakeRoutingEngine(),
            pricing_service=FakePricingService(),
            coverage_service=FakeCoverageService(),
        )

    app.dependency_overrides[route_module.get_calculate_route_use_case] = override_use_case
    app.dependency_overrides[route_proposals_module.get_calculate_route_use_case] = override_use_case

    response = client.post(
        "/api/v1/routes/proposals/detail",
        json={
            "start": {"lat": 5.3, "lng": -4.0},
            "end": {"lat": 5.31, "lng": -3.9},
            "profile": "car",
            "vehicle_width_m": 2.0,
            "vehicle_weight_t": 2.2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["proposals"][0]["enrichment"]["factors"]["degraded"] is True
    assert body["proposals"][0]["enrichment"]["troncons"][0]["road_name"] == "Route test"
    assert body["proposals"][0]["score_breakdown"]["vehicle_constraints"] == {
        "profile": "car",
        "width_m": 2.0,
        "weight_t": 2.2,
        "forbidden": False,
        "overweight": False,
        "too_wide": False,
        "eligible": True,
    }


def test_report_and_road_values_are_normalized() -> None:
    road_response = client.post(
        "/api/v1/roads",
        json={
            "name": "Route test",
            "geometry": {"type": "LineString", "coordinates": [[-4.02, 5.33], [-3.99, 5.34]]},
            "surface_state": "ok",
            "seasonal_practicability": "All_Year",
            "width_usable_m": 7.5,
            "is_blocked": False,
            "extra_metadata": {},
        },
    )
    assert road_response.status_code == 201
    assert road_response.json()["surface_state"] == "good"
    assert road_response.json()["seasonal_practicability"] == "all_year"

    report_response = client.post(
        "/api/v1/route-reports",
        json={
            "road_id": 1,
            "report_type": "peage",
            "severity": 2,
            "message": "Porte a peage",
            "geometry": {"lng": -4.01, "lat": 5.31},
            "extra_metadata": {},
        },
    )
    assert report_response.status_code == 201
    assert report_response.json()["report_type"] == "toll"


def test_roads_taxonomy_endpoint_lists_authorized_values() -> None:
    response = client.get("/api/v1/roads/taxonomy")
    assert response.status_code == 200
    body = response.json()
    assert "surface_state" in body
    assert "seasonal_practicability" in body
    assert "point_controle" in body
    assert "type_flux" in body
    assert set(body["vehicle_profiles"]) == {"car", "motorcycle", "truck"}
    assert "route_report_type" not in body


def test_route_reports_taxonomy_endpoint_lists_authorized_values() -> None:
    response = client.get("/api/v1/route-reports/taxonomy")
    assert response.status_code == 200
    assert "route_report_type" in response.json()
