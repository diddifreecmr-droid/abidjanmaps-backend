from geoalchemy2.elements import WKTElement

from app.modules.map_data.domain.taxonomy import (
    normalize_point_controle,
    normalize_road_surface_state,
    normalize_seasonal_practicability,
    normalize_type_flux,
)
from app.modules.map_data.domain.entities.place import Place
from app.modules.map_data.domain.entities.road import Road
from app.modules.map_data.infrastructure.persistence.models import PlaceORM, RoadORM


def line_string_to_wkt(geometry: dict) -> WKTElement:
    points = ", ".join(f"{lng} {lat}" for lng, lat in geometry["coordinates"])
    return WKTElement(f"LINESTRING({points})", srid=4326)


def point_to_wkt(geometry: dict) -> WKTElement:
    lng, lat = geometry["coordinates"]
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def road_to_orm(road: Road) -> RoadORM:
    return RoadORM(
        name=road.name,
        geom=line_string_to_wkt(road.geometry),
        surface_state=normalize_road_surface_state(road.surface_state),
        seasonal_practicability=normalize_seasonal_practicability(
            road.seasonal_practicability
        ),
        surface_reel=road.surface_reel,
        tonnage_max_reel_t=road.tonnage_max_reel_t,
        point_controle=normalize_point_controle(road.point_controle),
        temps_attente_p50_s=road.temps_attente_p50_s,
        temps_attente_p90_s=road.temps_attente_p90_s,
        eclairage=road.eclairage,
        securite_nuit=road.securite_nuit,
        width_usable_m=road.width_usable_m,
        pente_max_pct=road.pente_max_pct,
        type_flux=normalize_type_flux(road.type_flux),
        allowed_vehicle_profiles=road.allowed_vehicle_profiles,
        is_blocked=road.is_blocked,
        validation_status=road.validation_status,
        extra_metadata=road.metadata,
    )


def place_to_orm(place: Place) -> PlaceORM:
    return PlaceORM(
        name=place.name,
        category=place.category,
        location=point_to_wkt(place.location),
        aliases=place.aliases,
        vernacular_name=place.vernacular_name,
        description=place.description,
        verified=place.verified,
        validation_status=place.validation_status,
        extra_metadata=place.metadata,
    )
