from typing import Protocol


class RoadHistoryWriter(Protocol):
    async def add_history_entry(
        self,
        road_id: int,
        action: str,
        field_name: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> None: ...
