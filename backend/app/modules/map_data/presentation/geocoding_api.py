from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.map_data.infrastructure.persistence.place_repository import (
    SQLAlchemyPlaceRepository,
)
from app.modules.map_data.infrastructure.persistence.road_repository import (
    SQLAlchemyRoadRepository,
)
from app.modules.map_data.presentation.places_api import _place_location
from app.modules.map_data.presentation.roads_api import _road_geometry
from app.shared.infrastructure.db import get_async_session


router = APIRouter(tags=["geocoding"])


def _line_representative_location(geometry: dict[str, Any] | None) -> dict | None:
    if not geometry:
        return None
    coordinates = geometry.get("coordinates")
    if geometry.get("type") != "LineString" or not isinstance(coordinates, list):
        return None
    if not coordinates:
        return None
    lng, lat = coordinates[len(coordinates) // 2]
    return {"lng": lng, "lat": lat}


def _autocomplete_subtitle(item: dict) -> str:
    category = item.get("category") or item["type"]
    source = item.get("source") or "local"
    return f"{category} - {source}"


def _autocomplete_response(
    *,
    query: str,
    limit: int,
    results: list[dict],
) -> dict:
    items = [
        {
            "type": item["type"],
            "id": item["id"],
            "label": item["label"],
            "subtitle": _autocomplete_subtitle(item),
            "category": item.get("category"),
            "location": item["location"],
            "source": item.get("source", "local"),
            "metadata": item.get("metadata", {}),
        }
        for item in results[:limit]
    ]
    return {
        "status": "ok",
        "query": query,
        "count": len(items),
        "results": items,
    }


@router.get("/geocoding/search")
async def search_geocoding(
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

    per_type_limit = max(limit, 1)
    place_repository = SQLAlchemyPlaceRepository(session)
    road_repository = SQLAlchemyRoadRepository(session)

    places = await place_repository.search(
        q,
        limit=per_type_limit,
        bias_lat=bias_lat,
        bias_lng=bias_lng,
    )
    roads = await road_repository.search(
        q,
        limit=per_type_limit,
        bias_lat=bias_lat,
        bias_lng=bias_lng,
    )

    results: list[dict] = []
    for place in places:
        location = await _place_location(place, session)
        if location is None:
            continue
        results.append(
            {
                "type": "place",
                "id": place.id,
                "label": place.name,
                "category": place.category,
                "location": location,
                "source": (place.extra_metadata or {}).get("source", "local"),
                "metadata": place.extra_metadata or {},
            }
        )

    for road in roads:
        geometry = await _road_geometry(road, session)
        location = _line_representative_location(geometry)
        if location is None:
            continue
        results.append(
            {
                "type": "road",
                "id": road.id,
                "label": road.name,
                "category": "road",
                "location": location,
                "source": (road.extra_metadata or {}).get("source", "local"),
                "metadata": road.extra_metadata or {},
            }
        )

    return results[:limit]


@router.get("/geocoding/autocomplete")
async def autocomplete_geocoding(
    q: str = Query(min_length=2),
    limit: int = Query(default=8, ge=1, le=20),
    bias_lat: float | None = Query(default=None, ge=-90, le=90),
    bias_lng: float | None = Query(default=None, ge=-180, le=180),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    results = await search_geocoding(
        q=q,
        limit=limit,
        bias_lat=bias_lat,
        bias_lng=bias_lng,
        session=session,
    )
    return _autocomplete_response(query=q, limit=limit, results=results)
