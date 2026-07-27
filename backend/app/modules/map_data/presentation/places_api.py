import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.map_data.application.use_cases.update_map_data import UpdatePlace
from app.modules.map_data.domain.entities.place import Place
from app.shared.infrastructure.db import get_async_session
from app.modules.map_data.infrastructure.persistence.models import PlaceORM
from app.modules.map_data.infrastructure.persistence.place_repository import SQLAlchemyPlaceRepository
from app.modules.map_data.presentation.place_schemas import (
    PlaceCreateSchema,
    PlacePatchSchema,
    PlaceReadSchema,
)
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user, require_admin

router = APIRouter(tags=["places"])


def _point_to_geojson(schema) -> dict:
    return {"type": "Point", "coordinates": [schema.lng, schema.lat]}


def _geojson_point_to_lat_lng(geojson: dict | None) -> dict | None:
    if not geojson:
        return None
    lng, lat = geojson["coordinates"]
    return {"lng": lng, "lat": lat}


async def _place_location(place, session: AsyncSession) -> dict | None:
    if getattr(place, "location", None) is not None:
        location = place.location
        if "lat" in location and "lng" in location:
            return location
        return _geojson_point_to_lat_lng(location)
    if getattr(place, "id", None) is None or not hasattr(session, "scalar"):
        return None
    geojson = await session.scalar(
        select(func.ST_AsGeoJSON(PlaceORM.location)).where(PlaceORM.id == place.id)
    )
    return _geojson_point_to_lat_lng(json.loads(geojson)) if geojson else None


async def _place_response(place, session: AsyncSession) -> dict:
    return {
        "id": place.id,
        "name": place.name,
        "category": place.category,
        "location": await _place_location(place, session),
        "aliases": place.aliases,
        "vernacular_name": getattr(place, "vernacular_name", None),
        "description": place.description,
        "verified": place.verified,
        "validation_status": getattr(place, "validation_status", "proposed"),
        "extra_metadata": place.extra_metadata,
    }


@router.post("/places", response_model=PlaceReadSchema, status_code=201)
async def create_place(
    payload: PlaceCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> PlaceReadSchema:
    repo = SQLAlchemyPlaceRepository(session)
    place = Place(
        name=payload.name,
        category=payload.category,
        location=_point_to_geojson(payload.location),
        aliases=payload.aliases,
        vernacular_name=payload.vernacular_name,
        description=payload.description,
        verified=False,
        validation_status="proposed",
        metadata=payload.extra_metadata,
    )
    created = await repo.create(place, changed_by=current_user.email)
    return PlaceReadSchema(
        id=created.id or 0,
        verified=created.verified,
        validation_status=created.validation_status,
        **payload.model_dump(),
    )


@router.get("/places")
async def list_places(session: AsyncSession = Depends(get_async_session)) -> list[dict]:
    repo = SQLAlchemyPlaceRepository(session)
    places = await repo.list_all()
    return [await _place_response(place, session) for place in places]


@router.get("/places/search")
async def search_places(
    q: str = Query(min_length=1),
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    repo = SQLAlchemyPlaceRepository(session)
    places = await repo.search(q)
    return [await _place_response(place, session) for place in places]


@router.get("/places/{place_id}")
async def get_place(place_id: int, session: AsyncSession = Depends(get_async_session)) -> dict:
    repo = SQLAlchemyPlaceRepository(session)
    place = await repo.get_by_id(place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return await _place_response(place, session)


@router.patch("/places/{place_id}")
async def update_place(
    place_id: int,
    payload: PlacePatchSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    changes = payload.model_dump(
        exclude_unset=True,
        exclude={"note"},
    )
    if payload.location is not None:
        changes["location"] = _point_to_geojson(payload.location)
    place = await UpdatePlace(SQLAlchemyPlaceRepository(session)).execute(
        place_id=place_id,
        changes=changes,
        changed_by=current_user.email,
        note=payload.note,
    )
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return await _place_response(place, session)


@router.post("/places/{place_id}/validate")
async def validate_place(
    place_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
) -> dict:
    repo = SQLAlchemyPlaceRepository(session)
    place = await repo.set_validation_status(
        place_id,
        "validated",
        changed_by=current_user.email,
    )
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return await _place_response(place, session)


@router.post("/places/{place_id}/reject")
async def reject_place(
    place_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
) -> dict:
    repo = SQLAlchemyPlaceRepository(session)
    place = await repo.set_validation_status(
        place_id,
        "rejected",
        changed_by=current_user.email,
    )
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return await _place_response(place, session)


@router.get("/places/{place_id}/history")
async def place_history(place_id: int, session: AsyncSession = Depends(get_async_session)) -> list[dict]:
    repo = SQLAlchemyPlaceRepository(session)
    items = await repo.list_history(place_id)
    return [
        {
            "id": item.id,
            "place_id": item.place_id,
            "action": item.action,
            "field_name": item.field_name,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "changed_by": item.changed_by,
            "note": item.note,
            "created_at": item.created_at,
        }
        for item in items
    ]
