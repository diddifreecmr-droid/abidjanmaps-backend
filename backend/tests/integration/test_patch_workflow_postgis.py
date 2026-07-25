import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.modules.local_enrichment.application.use_cases.manage_route_reports import (
    RouteReportWorkflow,
)
from app.modules.local_enrichment.domain.entities.route_report import RouteReport
from app.modules.local_enrichment.infrastructure.persistence.route_report_repository import (
    SQLAlchemyRouteReportRepository,
)
from app.modules.map_data.application.use_cases.update_map_data import (
    UpdatePlace,
    UpdateRoad,
)
from app.modules.map_data.domain.entities.place import Place
from app.modules.map_data.domain.entities.road import Road
from app.modules.map_data.infrastructure.persistence.place_repository import (
    SQLAlchemyPlaceRepository,
)
from app.modules.map_data.infrastructure.persistence.road_repository import (
    SQLAlchemyRoadRepository,
)
from app.modules.users.application.use_cases.manage_users import UserService
from app.modules.users.infrastructure.persistence.user_repository import (
    SQLAlchemyUserRepository,
)
from app.modules.users.infrastructure.security.jwt_token_service import JWTTokenService
from app.modules.users.infrastructure.security.password_hasher import Argon2PasswordHasher


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGIS_INTEGRATION") != "1",
    reason="Set RUN_POSTGIS_INTEGRATION=1 to test the real PostGIS database",
)


def test_patch_workflows_with_real_postgis_and_rollback() -> None:
    asyncio.run(_run_workflows())


async def _run_workflows() -> None:
    database_url = os.environ["DATABASE_URL"]
    test_engine = create_async_engine(database_url)

    async with test_engine.connect() as connection:
        outer_transaction = await connection.begin()
        try:
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            ) as session:
                road_repository = SQLAlchemyRoadRepository(session)
                road = await road_repository.create(
                    Road(
                        name=f"codex-road-{uuid4()}",
                        geometry={
                            "type": "LineString",
                            "coordinates": [[-4.02, 5.33], [-4.01, 5.34]],
                        },
                        surface_state="good",
                        seasonal_practicability="all_year",
                        allowed_vehicle_profiles=["car", "motorcycle"],
                    )
                )
                await road_repository.set_validation_status(road.id, "validated")
                updated_road = await UpdateRoad(road_repository).execute(
                    road_id=road.id,
                    changes={"surface_state": "damaged"},
                    changed_by="integration-test",
                )
                assert updated_road.validation_status == "proposed"
                assert updated_road.surface_state == "damaged"
                assert updated_road.allowed_vehicle_profiles == ["car", "motorcycle"]

                place_repository = SQLAlchemyPlaceRepository(session)
                place = await place_repository.create(
                    Place(
                        name=f"codex-place-{uuid4()}",
                        category="landmark",
                        location={"type": "Point", "coordinates": [-4.0, 5.3]},
                    )
                )
                await place_repository.set_validation_status(place.id, "validated")
                updated_place = await UpdatePlace(place_repository).execute(
                    place_id=place.id,
                    changes={"description": "Updated by integration test"},
                    changed_by="integration-test",
                )
                assert updated_place.validation_status == "proposed"
                assert updated_place.verified is False

                report_repository = SQLAlchemyRouteReportRepository(session)
                report_workflow = RouteReportWorkflow(
                    repository=report_repository,
                    road_history=road_repository,
                )
                report = await report_workflow.propose(
                    RouteReport(
                        road_id=road.id,
                        report_type="flood",
                        severity=3,
                        message="Integration test report",
                    )
                )
                await report_workflow.review(
                    report_id=report.id,
                    status="validated",
                    reviewed_by="integration-admin",
                )
                updated_report = await report_workflow.update(
                    report_id=report.id,
                    changes={"severity": 5},
                    changed_by="integration-test",
                )
                assert updated_report.validation_status == "proposed"
                assert updated_report.reviewed_by is None

                report_history = await report_repository.list_history(report.id)
                assert [entry.action for entry in report_history[:3]] == [
                    "update",
                    "validate",
                    "propose",
                ]

                user_service = UserService(
                    repository=SQLAlchemyUserRepository(session),
                    password_hasher=Argon2PasswordHasher(),
                    token_service=JWTTokenService(
                        secret_key="integration-secret-long-enough-for-hs256",
                        algorithm="HS256",
                        expire_minutes=5,
                    ),
                )
                user = await user_service.create_user(
                    email=f"codex-{uuid4()}@example.com",
                    password="integration-password",
                    role="admin",
                )
                authenticated_user, token = await user_service.authenticate(
                    email=user.email,
                    password="integration-password",
                )
                assert authenticated_user.id == user.id
                assert authenticated_user.role == "admin"
                assert token
        finally:
            if outer_transaction.is_active:
                await outer_transaction.rollback()

    await test_engine.dispose()
