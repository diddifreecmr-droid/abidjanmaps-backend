import logging
import time

import httpx

from app.modules.routing.application.ports.routing_engine import RoutingEngine
from app.modules.routing.domain.entities.coordinate import Coordinate
from app.modules.routing.domain.entities.route import Route
from app.shared.domain.exceptions import (
    InvalidRoutingResponseError,
    NoRouteFoundError,
    RoutingEngineUnavailableError,
    RoutingTimeoutError,
)
from app.shared.configuration.settings import settings


logger = logging.getLogger("abidjanmaps.osrm")


class OSRMRoutingEngine(RoutingEngine):
    def _build_url(self, start: Coordinate, end: Coordinate) -> str:
        osrm_profile = settings.osrm_profile
        return (
            f"{settings.osrm_base_url.rstrip('/')}/route/v1/{osrm_profile}/"
            f"{start.lng},{start.lat};{end.lng},{end.lat}"
        )

    def _request_osrm(
        self,
        start: Coordinate,
        end: Coordinate,
        request_id: str | None = None,
        alternatives: bool = False,
    ) -> dict:
        osrm_profile = settings.osrm_profile
        url = self._build_url(start, end)
        params = {"overview": "full", "geometries": "geojson", "steps": "false"}
        if alternatives:
            params["alternatives"] = "true"
        auth = None
        if settings.osrm_username and settings.osrm_password:
            auth = (settings.osrm_username, settings.osrm_password)

        started_at = time.perf_counter()
        logger.info(
            "calling osrm url=%s profile=%s auth=%s alternatives=%s",
            url,
            osrm_profile,
            "enabled" if auth else "disabled",
            alternatives,
            extra={"request_id": request_id or "-"},
        )
        try:
            response = httpx.get(
                url,
                params=params,
                timeout=settings.osrm_timeout_seconds,
                auth=auth,
            )
        except httpx.TimeoutException as exc:
            logger.error("osrm timeout after %.2fms", (time.perf_counter() - started_at) * 1000, extra={"request_id": request_id or "-"})
            raise RoutingTimeoutError("OSRM timed out") from exc
        except httpx.RequestError as exc:
            logger.error("osrm request error: %s", exc, extra={"request_id": request_id or "-"})
            raise RoutingEngineUnavailableError("OSRM unavailable") from exc

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "osrm response status=%s duration=%.2fms",
            response.status_code,
            elapsed_ms,
            extra={"request_id": request_id or "-"},
        )

        if response.status_code in (401, 403):
            raise RoutingEngineUnavailableError("OSRM authentication failed")
        if response.status_code >= 500:
            raise RoutingEngineUnavailableError("OSRM unavailable")
        if response.status_code >= 400:
            raise NoRouteFoundError("No route found")

        try:
            return response.json()
        except ValueError as exc:
            raise InvalidRoutingResponseError("Invalid OSRM response") from exc

    def calculate_route(
        self,
        start: Coordinate,
        end: Coordinate,
        profile: str,
        request_id: str | None = None,
    ) -> Route:
        payload = self._request_osrm(start, end, request_id=request_id, alternatives=False)
        routes = payload.get("routes") or []
        if not routes:
            raise NoRouteFoundError("No route found")

        route = routes[0]
        geometry = route.get("geometry")
        distance_m = route.get("distance")
        duration_s = route.get("duration")

        if not geometry or distance_m is None or duration_s is None:
            raise InvalidRoutingResponseError("Invalid OSRM response")

        return Route(
            geometry=geometry,
            distance_m=int(distance_m),
            duration_s=int(duration_s),
        )

    def calculate_routes(
        self,
        start: Coordinate,
        end: Coordinate,
        request_id: str | None = None,
        max_alternatives: int = 3,
    ) -> list[Route]:
        payload = self._request_osrm(start, end, request_id=request_id, alternatives=True)
        routes = payload.get("routes") or []
        if not routes:
            raise NoRouteFoundError("No route found")

        proposals: list[Route] = []
        for route in routes[:max_alternatives]:
            geometry = route.get("geometry")
            distance_m = route.get("distance")
            duration_s = route.get("duration")
            if not geometry or distance_m is None or duration_s is None:
                continue
            proposals.append(
                Route(
                    geometry=geometry,
                    distance_m=int(distance_m),
                    duration_s=int(duration_s),
                )
            )

        if not proposals:
            raise InvalidRoutingResponseError("Invalid OSRM response")
        return proposals
