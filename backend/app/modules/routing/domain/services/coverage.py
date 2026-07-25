from abc import ABC, abstractmethod

from app.modules.routing.domain.entities.coordinate import Coordinate


class CoverageService(ABC):
    @abstractmethod
    def is_covered(self, coordinate: Coordinate) -> bool:
        raise NotImplementedError
