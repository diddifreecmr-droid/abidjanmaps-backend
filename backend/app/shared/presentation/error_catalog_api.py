from fastapi import APIRouter

from app.shared.presentation.error_catalog import ERROR_CATALOG


router = APIRouter(tags=["errors"])


@router.get("/errors/catalog")
async def get_error_catalog() -> dict:
    return {
        "status": "ok",
        "service": "diddimap",
        "errors": ERROR_CATALOG,
    }
