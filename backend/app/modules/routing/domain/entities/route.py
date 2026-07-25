from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Route:
    geometry: dict[str, Any]
    distance_m: int
    duration_s: int
