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


def _format_location(location: tuple | list) -> str:
    parts: list[str] = []
    for item in location:
        if item == "body":
            continue
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
            continue
        parts.append(str(item))
    return ".".join(parts) if parts else "body"


def _format_validation_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        error_type = str(error.get("type", "validation_error"))
        reason = str(error.get("msg", "Invalid value"))
        field = _format_location(error.get("loc", ("body",)))
        if error_type == "json_invalid":
            reason = "Invalid JSON body. Check quotes, commas and braces."
            field = "body"
        details.append(
            {
                "field": field,
                "reason": reason,
                "type": error_type,
            }
        )
    return details


def _validation_message(details: list[dict[str, str]]) -> str:
    if any(detail["type"] == "json_invalid" for detail in details):
        return "Invalid JSON body. Check quotes, commas and braces."
    if len(details) == 1:
        detail = details[0]
        return f"Invalid field '{detail['field']}': {detail['reason']}"
    return "Invalid request body. Check the details field."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = _format_validation_errors(exc)
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "invalid_request",
                "message": _validation_message(details),
                "details": details,
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
