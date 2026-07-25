from app.modules.routing.domain.entities.coordinate import Coordinate
from app.modules.routing.domain.services.coverage import CoverageService
from app.shared.configuration.settings import settings


class BoundingBoxCoverageService(CoverageService):
    def is_covered(self, coordinate: Coordinate) -> bool:
        return (
            settings.coverage_min_lat <= coordinate.lat <= settings.coverage_max_lat
            and settings.coverage_min_lng <= coordinate.lng <= settings.coverage_max_lng
        )
