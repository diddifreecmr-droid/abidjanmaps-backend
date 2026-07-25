from abc import ABC, abstractmethod

from app.modules.routing.application.services.route_enrichment_models import RouteEnrichmentDetail
from app.modules.routing.application.services.route_scoring import RouteLocalFactors
from app.shared.domain.vehicle import VehicleContext


class RouteEnrichmentRepository(ABC):
    @abstractmethod
    async def build_factors_from_route_geometry(
        self,
        route_geometry: dict,
        vehicle: VehicleContext | None = None,
    ) -> RouteLocalFactors:
        raise NotImplementedError

    @abstractmethod
    async def build_detail_from_route_geometry(
        self,
        route_geometry: dict,
        vehicle: VehicleContext | None = None,
    ) -> RouteEnrichmentDetail:
        raise NotImplementedError
