from app.modules.routing.domain.entities.coordinate import Coordinate
from app.modules.routing.infrastructure.coverage.bounding_box_coverage import (
    BoundingBoxCoverageService,
)


def test_coverage_detects_inside_zone() -> None:
    service = BoundingBoxCoverageService()
    assert service.is_covered(Coordinate(lat=5.33, lng=-4.02))


def test_coverage_detects_outside_zone() -> None:
    service = BoundingBoxCoverageService()
    assert not service.is_covered(Coordinate(lat=8.0, lng=-4.02))
