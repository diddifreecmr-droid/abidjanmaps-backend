from abc import ABC, abstractmethod

from app.modules.map_data.domain.entities.road import Road


class RoadRepository(ABC):
    @abstractmethod
    async def create(
        self,
        road: Road,
        changed_by: str | None = None,
    ) -> Road:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        road_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> object | None:
        raise NotImplementedError

    @abstractmethod
    async def add_history_entry(
        self,
        road_id: int,
        action: str,
        field_name: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> None:
        raise NotImplementedError
