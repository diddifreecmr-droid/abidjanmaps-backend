from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.db import get_async_session
from app.shared.infrastructure.health import check_database

router = APIRouter(tags=["health"])


@router.get("/db-health")
async def db_health(session: AsyncSession = Depends(get_async_session)) -> dict[str, str]:
    healthy = await check_database(session)
    return {
        "status": "ok" if healthy else "error",
        "service": "map-routing-service",
        "database": "available" if healthy else "unavailable",
    }
