import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.map_data.application.ports.road_repository import RoadRepository
from app.modules.map_data.domain.entities.road import Road
from app.modules.map_data.infrastructure.persistence.mappers import (
    line_string_to_wkt,
    road_to_orm,
)
from app.modules.map_data.infrastructure.persistence.models import RoadHistoryORM, RoadORM


class SQLAlchemyRoadRepository(RoadRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        road: Road,
        changed_by: str | None = None,
    ) -> Road:
        orm = road_to_orm(road)
        self.session.add(orm)
        await self.session.flush()
        self.session.add(
            RoadHistoryORM(
                road_id=orm.id,
                action="create",
                field_name=None,
                old_value=None,
                new_value={"validation_status": road.validation_status},
                changed_by=changed_by,
                note="Road created",
            )
        )
        await self.session.commit()
        await self.session.refresh(orm)
        return Road(
            id=orm.id,
            name=road.name,
            geometry=road.geometry,
            surface_state=road.surface_state,
            seasonal_practicability=road.seasonal_practicability,
            surface_reel=road.surface_reel,
            tonnage_max_reel_t=road.tonnage_max_reel_t,
            point_controle=road.point_controle,
            temps_attente_p50_s=road.temps_attente_p50_s,
            temps_attente_p90_s=road.temps_attente_p90_s,
            eclairage=road.eclairage,
            securite_nuit=road.securite_nuit,
            width_usable_m=road.width_usable_m,
            pente_max_pct=road.pente_max_pct,
            type_flux=road.type_flux,
            allowed_vehicle_profiles=road.allowed_vehicle_profiles,
            is_blocked=road.is_blocked,
            validation_status=road.validation_status,
            metadata=road.metadata,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def list_all(self) -> list[RoadORM]:
        result = await self.session.execute(select(RoadORM).order_by(RoadORM.id.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, road_id: int) -> RoadORM | None:
        result = await self.session.execute(select(RoadORM).where(RoadORM.id == road_id))
        return result.scalar_one_or_none()

    async def update(
        self,
        road_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> RoadORM | None:
        road = await self.get_by_id(road_id)
        if road is None:
            return None

        field_mapping = {
            "name": "name",
            "geometry": "geom",
            "surface_state": "surface_state",
            "seasonal_practicability": "seasonal_practicability",
            "surface_reel": "surface_reel",
            "tonnage_max_reel_t": "tonnage_max_reel_t",
            "point_controle": "point_controle",
            "temps_attente_p50_s": "temps_attente_p50_s",
            "temps_attente_p90_s": "temps_attente_p90_s",
            "eclairage": "eclairage",
            "securite_nuit": "securite_nuit",
            "width_usable_m": "width_usable_m",
            "pente_max_pct": "pente_max_pct",
            "type_flux": "type_flux",
            "allowed_vehicle_profiles": "allowed_vehicle_profiles",
            "is_blocked": "is_blocked",
            "extra_metadata": "extra_metadata",
            "validation_status": "validation_status",
        }
        old_values: dict = {}
        new_values: dict = {}

        for field_name, value in changes.items():
            orm_field = field_mapping.get(field_name)
            if orm_field is None:
                continue
            if field_name == "geometry":
                old_geometry = await self.session.scalar(
                    select(func.ST_AsGeoJSON(RoadORM.geom)).where(RoadORM.id == road_id)
                )
                old_values[field_name] = json.loads(old_geometry) if old_geometry else None
                setattr(road, orm_field, line_string_to_wkt(value))
            else:
                old_values[field_name] = getattr(road, orm_field)
                setattr(road, orm_field, value)
            new_values[field_name] = value

        await self.session.flush()
        self.session.add(
            RoadHistoryORM(
                road_id=road_id,
                action="update",
                field_name=next(iter(new_values)) if len(new_values) == 1 else "multiple",
                old_value=old_values,
                new_value=new_values,
                changed_by=changed_by,
                note=note,
            )
        )
        await self.session.commit()
        await self.session.refresh(road)
        return road

    async def set_validation_status(
        self,
        road_id: int,
        status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> RoadORM | None:
        road = await self.get_by_id(road_id)
        if road is None:
            return None
        old_status = road.validation_status
        road.validation_status = status
        await self.session.flush()
        self.session.add(
            RoadHistoryORM(
                road_id=road_id,
                action="validate" if status == "validated" else "reject",
                field_name="validation_status",
                old_value={"validation_status": old_status},
                new_value={"validation_status": status},
                changed_by=changed_by,
                note=note,
            )
        )
        await self.session.commit()
        await self.session.refresh(road)
        return road

    async def list_history(self, road_id: int) -> list[RoadHistoryORM]:
        result = await self.session.execute(
            select(RoadHistoryORM).where(RoadHistoryORM.road_id == road_id).order_by(RoadHistoryORM.id.desc())
        )
        return list(result.scalars().all())

    async def add_history_entry(
        self,
        road_id: int,
        action: str,
        field_name: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> None:
        if not hasattr(self.session, "add"):
            return
        self.session.add(
            RoadHistoryORM(
                road_id=road_id,
                action=action,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                changed_by=changed_by,
                note=note,
            )
        )
        await self.session.commit()
