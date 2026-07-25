from abc import ABC, abstractmethod

from app.modules.local_enrichment.domain.entities.route_report import RouteReport


class RouteReportRepository(ABC):
    @abstractmethod
    async def create(self, report: RouteReport) -> RouteReport:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self, validation_status: str | None = None) -> list[RouteReport]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, report_id: int) -> RouteReport | None:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        report_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> RouteReport | None:
        raise NotImplementedError

    @abstractmethod
    async def set_validation_status(
        self,
        report_id: int,
        status: str,
        reviewed_by: str | None = None,
        note: str | None = None,
    ) -> RouteReport | None:
        raise NotImplementedError

    @abstractmethod
    async def list_history(self, report_id: int) -> list[object]:
        raise NotImplementedError
