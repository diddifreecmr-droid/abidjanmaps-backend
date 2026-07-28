from typing import Any

from fastapi import APIRouter, Depends, Query
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


@router.get("/geocoding/search")
async def search_geocoding(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    per_type_limit = max(limit, 1)
    place_repository = SQLAlchemyPlaceRepository(session)
    road_repository = SQLAlchemyRoadRepository(session)

    places = (await place_repository.search(q))[:per_type_limit]
    roads = await road_repository.search(q, limit=per_type_limit)

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
