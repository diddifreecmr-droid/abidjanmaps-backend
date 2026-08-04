import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.map_data.application.use_cases.update_map_data import UpdateRoad
from app.modules.map_data.domain.entities.road import Road
from app.modules.map_data.domain.taxonomy import road_taxonomy_documentation
from app.shared.infrastructure.db import get_async_session
from app.modules.map_data.infrastructure.persistence.models import RoadORM
from app.modules.map_data.infrastructure.persistence.road_repository import SQLAlchemyRoadRepository
from app.modules.map_data.presentation.road_schemas import (
    RoadCreateSchema,
    RoadPatchSchema,
    RoadReadSchema,
)
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import get_current_user, require_admin

router = APIRouter(tags=["roads"])


@router.get("/roads/taxonomy")
async def roads_taxonomy() -> dict:
    return road_taxonomy_documentation()


def _line_string_to_geojson(schema) -> dict:
    return {"type": schema.type, "coordinates": schema.coordinates}


async def _road_geometry(road, session: AsyncSession) -> dict | None:
    if getattr(road, "geometry", None) is not None:
        return road.geometry
    if getattr(road, "id", None) is None or not hasattr(session, "scalar"):
        return None
    geojson = await session.scalar(
        select(func.ST_AsGeoJSON(RoadORM.geom)).where(RoadORM.id == road.id)
    )
    return json.loads(geojson) if geojson else None


async def _road_response(road, session: AsyncSession) -> dict:
    return {
        "id": road.id,
        "name": road.name,
        "geometry": await _road_geometry(road, session),
        "surface_state": road.surface_state,
        "seasonal_practicability": road.seasonal_practicability,
        "surface_reel": getattr(road, "surface_reel", None),
        "tonnage_max_reel_t": getattr(road, "tonnage_max_reel_t", None),
        "point_controle": getattr(road, "point_controle", None),
        "temps_attente_p50_s": getattr(road, "temps_attente_p50_s", None),
        "temps_attente_p90_s": getattr(road, "temps_attente_p90_s", None),
        "eclairage": getattr(road, "eclairage", None),
        "securite_nuit": getattr(road, "securite_nuit", None),
        "width_usable_m": road.width_usable_m,
        "pente_max_pct": getattr(road, "pente_max_pct", None),
        "type_flux": getattr(road, "type_flux", None),
        "allowed_vehicle_profiles": getattr(
            road,
            "allowed_vehicle_profiles",
            ["car", "motorcycle", "truck"],
        ),
        "is_blocked": road.is_blocked,
        "validation_status": getattr(road, "validation_status", "proposed"),
        "extra_metadata": road.extra_metadata,
    }


@router.post("/roads", response_model=RoadReadSchema, status_code=201)
async def create_road(
    payload: RoadCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> RoadReadSchema:
    repo = SQLAlchemyRoadRepository(session)
    road = Road(
        name=payload.name,
        geometry=_line_string_to_geojson(payload.geometry),
        surface_state=payload.surface_state,
        seasonal_practicability=payload.seasonal_practicability,
        surface_reel=payload.surface_reel,
        tonnage_max_reel_t=payload.tonnage_max_reel_t,
        point_controle=payload.point_controle,
        temps_attente_p50_s=payload.temps_attente_p50_s,
        temps_attente_p90_s=payload.temps_attente_p90_s,
        eclairage=payload.eclairage,
        securite_nuit=payload.securite_nuit,
        width_usable_m=payload.width_usable_m,
        pente_max_pct=payload.pente_max_pct,
        type_flux=payload.type_flux,
        allowed_vehicle_profiles=payload.allowed_vehicle_profiles,
        is_blocked=payload.is_blocked,
        metadata=payload.extra_metadata,
    )
    created = await repo.create(road, changed_by=current_user.email)
    return RoadReadSchema(
        id=created.id or 0,
        validation_status=created.validation_status,
        **payload.model_dump(),
    )


@router.get("/roads")
async def list_roads(session: AsyncSession = Depends(get_async_session)) -> list[dict]:
    repo = SQLAlchemyRoadRepository(session)
    roads = await repo.list_all()
    return [await _road_response(road, session) for road in roads]


@router.get("/roads/search")
async def search_roads(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    bias_lat: float | None = Query(default=None, ge=-90, le=90),
    bias_lng: float | None = Query(default=None, ge=-180, le=180),
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    if (bias_lat is None) != (bias_lng is None):
        raise HTTPException(
            status_code=400,
            detail="bias_lat and bias_lng must be provided together",
        )

    repo = SQLAlchemyRoadRepository(session)
    roads = await repo.search(
        q,
        limit=limit,
        bias_lat=bias_lat,
        bias_lng=bias_lng,
    )
    return [await _road_response(road, session) for road in roads]


@router.get("/roads/{road_id}")
async def get_road(road_id: int, session: AsyncSession = Depends(get_async_session)) -> dict:
    repo = SQLAlchemyRoadRepository(session)
    road = await repo.get_by_id(road_id)
    if road is None:
        raise HTTPException(status_code=404, detail="Road not found")
    return await _road_response(road, session)


@router.patch("/roads/{road_id}")
async def update_road(
    road_id: int,
    payload: RoadPatchSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    changes = payload.model_dump(
        exclude_unset=True,
        exclude={"note"},
    )
    if payload.geometry is not None:
        changes["geometry"] = _line_string_to_geojson(payload.geometry)
    road = await UpdateRoad(SQLAlchemyRoadRepository(session)).execute(
        road_id=road_id,
        changes=changes,
        changed_by=current_user.email,
        note=payload.note,
    )
    if road is None:
        raise HTTPException(status_code=404, detail="Road not found")
    return await _road_response(road, session)


@router.post("/roads/{road_id}/validate")
async def validate_road(
    road_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
) -> dict:
    repo = SQLAlchemyRoadRepository(session)
    road = await repo.set_validation_status(
        road_id,
        "validated",
        changed_by=current_user.email,
    )
    if road is None:
        raise HTTPException(status_code=404, detail="Road not found")
    return await _road_response(road, session)


@router.post("/roads/{road_id}/reject")
async def reject_road(
    road_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
) -> dict:
    repo = SQLAlchemyRoadRepository(session)
    road = await repo.set_validation_status(
        road_id,
        "rejected",
        changed_by=current_user.email,
    )
    if road is None:
        raise HTTPException(status_code=404, detail="Road not found")
    return await _road_response(road, session)


@router.get("/roads/{road_id}/history")
async def road_history(road_id: int, session: AsyncSession = Depends(get_async_session)) -> list[dict]:
    repo = SQLAlchemyRoadRepository(session)
    items = await repo.list_history(road_id)
    return [
        {
            "id": item.id,
            "road_id": item.road_id,
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
