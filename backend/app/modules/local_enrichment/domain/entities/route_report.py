from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.modules.local_enrichment.domain.taxonomy import normalize_route_report_type


VALIDATION_STATUSES = frozenset({"proposed", "validated", "rejected"})


@dataclass(frozen=True, kw_only=True)
class RouteReport:
    id: int | None = None
    road_id: int | None
    report_type: str
    severity: int
    message: str
    geometry: dict[str, Any] | None = None
    reported_by: str | None = None
    validation_status: str = "proposed"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    reported_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_type", normalize_route_report_type(self.report_type))
        if self.validation_status not in VALIDATION_STATUSES:
            raise ValueError(f"Unsupported validation status: {self.validation_status}")
