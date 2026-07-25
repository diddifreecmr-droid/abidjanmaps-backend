from app.modules.routing.application.ports.route_enrichment_repository import RouteEnrichmentRepository
from app.modules.routing.application.services.route_enrichment_models import RouteEnrichmentDetail
from app.modules.routing.application.services.route_scoring import RouteLocalFactors
from app.shared.domain.vehicle import VehicleContext


class RouteEnrichmentService:
    def __init__(self, repository: RouteEnrichmentRepository) -> None:
        self.repository = repository

    async def build_factors_from_route_geometry(
        self,
        route_geometry: dict,
        vehicle: VehicleContext | None = None,
    ) -> RouteLocalFactors:
        return await self.repository.build_factors_from_route_geometry(
            route_geometry,
            vehicle,
        )

    async def build_detail_from_route_geometry(
        self,
        route_geometry: dict,
        vehicle: VehicleContext | None = None,
    ) -> RouteEnrichmentDetail:
        return await self.repository.build_detail_from_route_geometry(
            route_geometry,
            vehicle,
        )
