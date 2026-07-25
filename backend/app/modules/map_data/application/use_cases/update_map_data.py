from app.modules.map_data.application.ports.place_repository import PlaceRepository
from app.modules.map_data.application.ports.road_repository import RoadRepository


class UpdateRoad:
    def __init__(self, repository: RoadRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        road_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> object | None:
        unpublished_changes = {
            **changes,
            "validation_status": "proposed",
        }
        return await self.repository.update(
            road_id=road_id,
            changes=unpublished_changes,
            changed_by=changed_by,
            note=note,
        )


class UpdatePlace:
    def __init__(self, repository: PlaceRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        place_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> object | None:
        unpublished_changes = {
            **changes,
            "validation_status": "proposed",
            "verified": False,
        }
        return await self.repository.update(
            place_id=place_id,
            changes=unpublished_changes,
            changed_by=changed_by,
            note=note,
        )
