from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, kw_only=True)
class Place:
    id: int | None = None
    name: str
    category: str
    location: dict[str, Any]
    aliases: list[str] = field(default_factory=list)
    vernacular_name: str | None = None
    description: str | None = None
    verified: bool = False
    validation_status: str = "proposed"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
