from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.shared.domain.exceptions import (
    DomainError,
    InvalidProfileError,
    InvalidRoutingResponseError,
    NoRouteFoundError,
    OutOfCoverageError,
    RoutingEngineUnavailableError,
    RoutingTimeoutError,
)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "code": code, "message": message},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "invalid_request",
                "message": "Description lisible de l'erreur",
            },
        )

    @app.exception_handler(InvalidProfileError)
    async def invalid_profile_handler(_: Request, exc: InvalidProfileError) -> JSONResponse:
        return _error(400, "invalid_request", str(exc))

    @app.exception_handler(OutOfCoverageError)
    async def out_of_coverage_handler(_: Request, exc: OutOfCoverageError) -> JSONResponse:
        return _error(409, "out_of_coverage", str(exc))

    @app.exception_handler(NoRouteFoundError)
    async def no_route_found_handler(_: Request, exc: NoRouteFoundError) -> JSONResponse:
        return _error(404, "no_route_found", str(exc))

    @app.exception_handler(RoutingEngineUnavailableError)
    async def routing_unavailable_handler(_: Request, exc: RoutingEngineUnavailableError) -> JSONResponse:
        return _error(503, "routing_engine_unavailable", str(exc))

    @app.exception_handler(RoutingTimeoutError)
    async def routing_timeout_handler(_: Request, exc: RoutingTimeoutError) -> JSONResponse:
        return _error(504, "routing_timeout", str(exc))

    @app.exception_handler(InvalidRoutingResponseError)
    async def invalid_routing_response_handler(_: Request, exc: InvalidRoutingResponseError) -> JSONResponse:
        return _error(502, "invalid_routing_response", str(exc))

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return _error(500, "internal_error", str(exc))
