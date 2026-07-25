from abc import ABC, abstractmethod

from app.modules.routing.domain.entities.coordinate import Coordinate
from app.modules.routing.domain.entities.route import Route


class RoutingEngine(ABC):
    @abstractmethod
    def calculate_route(
        self,
        start: Coordinate,
        end: Coordinate,
        profile: str,
        request_id: str | None = None,
    ) -> Route:
        raise NotImplementedError
