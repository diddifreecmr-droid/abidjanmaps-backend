import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.bootstrap.api import router as api_router
from app.shared.presentation.exception_handlers import register_exception_handlers
from app.shared.infrastructure.logging import configure_logging


logger = logging.getLogger("abidjanmaps.api")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="AbidjanMaps Routing Service",
        version="1.0.0",
        description="Backend V1 for route calculation, pricing, and coverage validation.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"^https?://(localhost|127\.0\.0\.1|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "%s %s completed in %.2fms",
                request.method,
                request.url.path,
                duration_ms,
                extra={"request_id": request_id},
            )
        if response is None:
            raise RuntimeError("Request processing failed before response creation")
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
