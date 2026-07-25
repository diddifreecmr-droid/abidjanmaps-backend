from fastapi import APIRouter

from app.modules.local_enrichment.presentation.api import router as route_reports_router
from app.modules.map_data.presentation.places_api import router as places_router
from app.modules.map_data.presentation.roads_api import router as roads_router
from app.modules.routing.presentation.proposal_api import router as route_proposals_router
from app.modules.routing.presentation.route_api import router as route_router
from app.modules.users.presentation.api import router as users_router
from app.shared.presentation.db_health_api import router as db_health_router
from app.shared.presentation.health_api import router as health_router

router = APIRouter()
router.include_router(health_router)
router.include_router(db_health_router)
router.include_router(users_router)
router.include_router(roads_router)
router.include_router(places_router)
router.include_router(route_reports_router)
router.include_router(route_proposals_router)
router.include_router(route_router)
