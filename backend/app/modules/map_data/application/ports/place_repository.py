from abc import ABC, abstractmethod

from app.modules.map_data.domain.entities.place import Place


class PlaceRepository(ABC):
    @abstractmethod
    async def create(
        self,
        place: Place,
        changed_by: str | None = None,
    ) -> Place:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        place_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> object | None:
        raise NotImplementedError
