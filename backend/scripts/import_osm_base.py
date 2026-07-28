import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.modules.map_data.infrastructure.persistence.models import PlaceORM, RoadORM
from app.shared.infrastructure.db import async_session_factory

try:
    import osmium
except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing.
    osmium = None
    OSMIUM_IMPORT_ERROR = exc
else:
    OSMIUM_IMPORT_ERROR = None

OsmiumSimpleHandler = osmium.SimpleHandler if osmium is not None else object


DEFAULT_ABIDJAN_BBOX = "-4.25,5.15,-3.70,5.55"
DEFAULT_PBF_NAME = "ivory-coast-latest.osm.pbf"
OSM_ACTOR = "osm-import"


@dataclass(frozen=True, kw_only=True)
class ImportedRoad:
    osm_type: str
    osm_id: int
    name: str
    geometry: dict[str, Any]
    tags: dict[str, str]


@dataclass(frozen=True, kw_only=True)
class ImportedPlace:
    osm_type: str
    osm_id: int
    name: str
    category: str
    location: dict[str, Any]
    aliases: list[str]
    tags: dict[str, str]


def _env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


def _env_int(name: str, default: int) -> int:
    raw = _env_value(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _default_pbf_path() -> Path:
    candidates = [
        Path("/data/osrm") / DEFAULT_PBF_NAME,
        Path(__file__).resolve().parents[2] / "data" / "osrm" / DEFAULT_PBF_NAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if value is None or value.strip().lower() in {"", "none", "all"}:
        return None
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("OSM_IMPORT_BBOX must be min_lng,min_lat,max_lng,max_lat")
    min_lng, min_lat, max_lng, max_lat = parts
    if min_lng >= max_lng or min_lat >= max_lat:
        raise ValueError("OSM_IMPORT_BBOX has invalid min/max values")
    return min_lng, min_lat, max_lng, max_lat


def _in_bbox(lng: float, lat: float, bbox: tuple[float, float, float, float] | None) -> bool:
    if bbox is None:
        return True
    min_lng, min_lat, max_lng, max_lat = bbox
    return min_lng <= lng <= max_lng and min_lat <= lat <= max_lat


def _tags(entity: Any) -> dict[str, str]:
    return {tag.k: tag.v for tag in entity.tags}


def _aliases(tags: dict[str, str]) -> list[str]:
    values: list[str] = []
    for key in ("alt_name", "short_name", "loc_name", "official_name", "name:fr"):
        value = tags.get(key)
        if not value:
            continue
        values.extend(part.strip() for part in value.split(";") if part.strip())
    name = tags.get("name")
    return [value for value in dict.fromkeys(values) if value != name]


def _place_category(tags: dict[str, str]) -> str | None:
    for key in (
        "amenity",
        "shop",
        "tourism",
        "leisure",
        "office",
        "healthcare",
        "aeroway",
        "public_transport",
        "railway",
        "place",
    ):
        value = tags.get(key)
        if value:
            return value[:80]
    return None


def _surface_state(tags: dict[str, str]) -> str:
    surface = (tags.get("surface") or "").lower()
    smoothness = (tags.get("smoothness") or "").lower()
    if surface in {"asphalt", "concrete", "paved", "concrete:plates"}:
        return "good"
    if surface in {"unpaved", "compacted", "gravel", "fine_gravel"}:
        return "fair"
    if surface in {"dirt", "earth", "ground", "sand"}:
        return "degraded"
    if smoothness in {"bad", "very_bad", "horrible", "very_horrible", "impassable"}:
        return "bad"
    return "fair"


def _type_flux(tags: dict[str, str]) -> str:
    if tags.get("toll") == "yes":
        return "toll"
    if tags.get("access") in {"private", "no", "destination"}:
        return "restricted"
    return "free"


def _allowed_vehicle_profiles(tags: dict[str, str]) -> list[str]:
    highway = tags.get("highway")
    if highway in {"footway", "path", "pedestrian", "steps"}:
        return ["motorcycle"]
    if tags.get("motor_vehicle") in {"no", "private"}:
        return ["motorcycle"]
    return ["car", "motorcycle", "truck"]


def _point_to_wkt(geometry: dict[str, Any]) -> WKTElement:
    lng, lat = geometry["coordinates"]
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def _line_to_wkt(geometry: dict[str, Any]) -> WKTElement:
    points = ", ".join(f"{lng} {lat}" for lng, lat in geometry["coordinates"])
    return WKTElement(f"LINESTRING({points})", srid=4326)


def _way_coordinates(way: Any) -> list[list[float]]:
    coordinates: list[list[float]] = []
    for node in way.nodes:
        try:
            if node.location.valid():
                point = [round(float(node.lon), 7), round(float(node.lat), 7)]
                if not coordinates or coordinates[-1] != point:
                    coordinates.append(point)
        except Exception:
            continue
    return coordinates


def _centroid(coordinates: list[list[float]]) -> dict[str, Any] | None:
    if not coordinates:
        return None
    lng = sum(point[0] for point in coordinates) / len(coordinates)
    lat = sum(point[1] for point in coordinates) / len(coordinates)
    return {"type": "Point", "coordinates": [round(lng, 7), round(lat, 7)]}


class OsmBaseHandler(OsmiumSimpleHandler):  # type: ignore[misc, valid-type]
    def __init__(
        self,
        *,
        bbox: tuple[float, float, float, float] | None,
        max_roads: int,
        max_places: int,
    ) -> None:
        super().__init__()
        self.bbox = bbox
        self.max_roads = max_roads
        self.max_places = max_places
        self.roads: list[ImportedRoad] = []
        self.places: list[ImportedPlace] = []

    def node(self, node: Any) -> None:
        if self.max_places and len(self.places) >= self.max_places:
            return
        tags = _tags(node)
        name = tags.get("name")
        category = _place_category(tags)
        if not name or category is None:
            return
        try:
            if not node.location.valid():
                return
            lng = round(float(node.location.lon), 7)
            lat = round(float(node.location.lat), 7)
        except Exception:
            return
        if not _in_bbox(lng, lat, self.bbox):
            return
        self.places.append(
            ImportedPlace(
                osm_type="node",
                osm_id=int(node.id),
                name=name[:255],
                category=category,
                location={"type": "Point", "coordinates": [lng, lat]},
                aliases=_aliases(tags),
                tags=tags,
            )
        )

    def way(self, way: Any) -> None:
        tags = _tags(way)
        name = tags.get("name")
        coordinates = _way_coordinates(way)
        if len(coordinates) < 2:
            return
        if not any(_in_bbox(lng, lat, self.bbox) for lng, lat in coordinates):
            return

        highway = tags.get("highway")
        if (
            name
            and highway
            and highway
            not in {"construction", "proposed", "raceway", "platform"}
            and (not self.max_roads or len(self.roads) < self.max_roads)
        ):
            self.roads.append(
                ImportedRoad(
                    osm_type="way",
                    osm_id=int(way.id),
                    name=name[:255],
                    geometry={"type": "LineString", "coordinates": coordinates},
                    tags=tags,
                )
            )

        category = _place_category(tags)
        if (
            name
            and category is not None
            and (not self.max_places or len(self.places) < self.max_places)
        ):
            location = _centroid(coordinates)
            if location is not None:
                self.places.append(
                    ImportedPlace(
                        osm_type="way",
                        osm_id=int(way.id),
                        name=name[:255],
                        category=category,
                        location=location,
                        aliases=_aliases(tags),
                        tags=tags,
                    )
                )


async def _existing_osm_keys(model: type[RoadORM] | type[PlaceORM]) -> set[tuple[str, int]]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(model.extra_metadata).where(
                model.extra_metadata["source"].astext == "osm"
            )
        )
        keys: set[tuple[str, int]] = set()
        for metadata in result.scalars().all():
            osm_type = metadata.get("osm_type")
            osm_id = metadata.get("osm_id")
            if osm_type is not None and osm_id is not None:
                keys.add((str(osm_type), int(osm_id)))
        return keys


async def _insert_roads(roads: list[ImportedRoad], *, batch_size: int) -> dict[str, int]:
    existing = await _existing_osm_keys(RoadORM)
    counters = {"created": 0, "skipped": 0}
    async with async_session_factory() as session:
        pending: list[RoadORM] = []
        for road in roads:
            key = (road.osm_type, road.osm_id)
            if key in existing:
                counters["skipped"] += 1
                continue
            metadata = {
                "source": "osm",
                "osm_type": road.osm_type,
                "osm_id": road.osm_id,
                "osm_highway": road.tags.get("highway"),
                "osm_tags": {
                    key: value
                    for key, value in road.tags.items()
                    if key
                    in {
                        "highway",
                        "surface",
                        "smoothness",
                        "access",
                        "toll",
                        "oneway",
                    }
                },
                "import_actor": OSM_ACTOR,
            }
            pending.append(
                RoadORM(
                    name=road.name,
                    geom=_line_to_wkt(road.geometry),
                    surface_state=_surface_state(road.tags),
                    seasonal_practicability="all_year",
                    surface_reel=road.tags.get("surface"),
                    type_flux=_type_flux(road.tags),
                    allowed_vehicle_profiles=_allowed_vehicle_profiles(road.tags),
                    is_blocked=False,
                    validation_status="validated",
                    extra_metadata=metadata,
                )
            )
            existing.add(key)
            counters["created"] += 1
            if len(pending) >= batch_size:
                session.add_all(pending)
                await session.commit()
                pending = []
        if pending:
            session.add_all(pending)
            await session.commit()
    return counters


async def _insert_places(places: list[ImportedPlace], *, batch_size: int) -> dict[str, int]:
    existing = await _existing_osm_keys(PlaceORM)
    counters = {"created": 0, "skipped": 0}
    async with async_session_factory() as session:
        pending: list[PlaceORM] = []
        for place in places:
            key = (place.osm_type, place.osm_id)
            if key in existing:
                counters["skipped"] += 1
                continue
            metadata = {
                "source": "osm",
                "osm_type": place.osm_type,
                "osm_id": place.osm_id,
                "osm_category": place.category,
                "osm_tags": {
                    key: value
                    for key, value in place.tags.items()
                    if key
                    in {
                        "amenity",
                        "shop",
                        "tourism",
                        "leisure",
                        "office",
                        "healthcare",
                        "aeroway",
                        "public_transport",
                        "railway",
                        "place",
                    }
                },
                "import_actor": OSM_ACTOR,
            }
            pending.append(
                PlaceORM(
                    name=place.name,
                    category=place.category,
                    location=_point_to_wkt(place.location),
                    aliases=place.aliases,
                    vernacular_name=place.tags.get("loc_name"),
                    description=place.tags.get("description"),
                    verified=True,
                    validation_status="validated",
                    extra_metadata=metadata,
                )
            )
            existing.add(key)
            counters["created"] += 1
            if len(pending) >= batch_size:
                session.add_all(pending)
                await session.commit()
                pending = []
        if pending:
            session.add_all(pending)
            await session.commit()
    return counters


async def import_osm_base() -> dict[str, Any]:
    if osmium is None:
        raise RuntimeError(
            "Unable to import dependency 'osmium'. "
            "If `pip freeze` shows osmium, the package may be installed but one of "
            f"its native libraries failed to load. Original error: {OSMIUM_IMPORT_ERROR!r}"
        )

    pbf_path = Path(_env_value("OSM_IMPORT_PBF_PATH") or _default_pbf_path())
    if not pbf_path.exists():
        raise FileNotFoundError(
            f"OSM PBF not found: {pbf_path}. Mount OSRM_DATA_PATH into backend or set OSM_IMPORT_PBF_PATH."
        )

    bbox = _parse_bbox(_env_value("OSM_IMPORT_BBOX", DEFAULT_ABIDJAN_BBOX))
    max_roads = _env_int("OSM_IMPORT_MAX_ROADS", 0)
    max_places = _env_int("OSM_IMPORT_MAX_PLACES", 0)
    batch_size = _env_int("OSM_IMPORT_BATCH_SIZE", 500)

    handler = OsmBaseHandler(
        bbox=bbox,
        max_roads=max_roads,
        max_places=max_places,
    )
    handler.apply_file(str(pbf_path), locations=True)

    road_counters = await _insert_roads(handler.roads, batch_size=batch_size)
    place_counters = await _insert_places(handler.places, batch_size=batch_size)

    return {
        "status": "ok",
        "pbf_path": str(pbf_path),
        "bbox": bbox,
        "parsed": {
            "roads": len(handler.roads),
            "places": len(handler.places),
        },
        "roads": road_counters,
        "places": place_counters,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(import_osm_base()), ensure_ascii=True))
