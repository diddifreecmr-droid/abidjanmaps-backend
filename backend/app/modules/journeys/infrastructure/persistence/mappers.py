import json

from geoalchemy2.elements import WKTElement


def point_to_wkt(location: dict[str, float]) -> WKTElement:
    return WKTElement(f"POINT({location['lng']} {location['lat']})", srid=4326)


def geojson_point_to_location(value: str | dict | None) -> dict[str, float] | None:
    if value is None:
        return None
    geojson = json.loads(value) if isinstance(value, str) else value
    lng, lat = geojson["coordinates"]
    return {"lng": lng, "lat": lat}
