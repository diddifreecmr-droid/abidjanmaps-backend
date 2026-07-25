import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.map_data.application.ports.place_repository import PlaceRepository
from app.modules.map_data.domain.entities.place import Place
from app.modules.map_data.infrastructure.persistence.mappers import (
    place_to_orm,
    point_to_wkt,
)
from app.modules.map_data.infrastructure.persistence.models import PlaceHistoryORM, PlaceORM


class SQLAlchemyPlaceRepository(PlaceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        place: Place,
        changed_by: str | None = None,
    ) -> Place:
        orm = place_to_orm(place)
        self.session.add(orm)
        await self.session.flush()
        self.session.add(
            PlaceHistoryORM(
                place_id=orm.id,
                action="create",
                field_name=None,
                old_value=None,
                new_value={"validation_status": place.validation_status},
                changed_by=changed_by,
                note="Place created",
            )
        )
        await self.session.commit()
        await self.session.refresh(orm)
        return Place(
            id=orm.id,
            name=place.name,
            category=place.category,
            location=place.location,
            aliases=place.aliases,
            vernacular_name=place.vernacular_name,
            description=place.description,
            verified=place.verified,
            validation_status=place.validation_status,
            metadata=place.metadata,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def list_all(self) -> list[PlaceORM]:
        result = await self.session.execute(select(PlaceORM).order_by(PlaceORM.id.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, place_id: int) -> PlaceORM | None:
        result = await self.session.execute(select(PlaceORM).where(PlaceORM.id == place_id))
        return result.scalar_one_or_none()

    async def update(
        self,
        place_id: int,
        changes: dict,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> PlaceORM | None:
        place = await self.get_by_id(place_id)
        if place is None:
            return None

        field_mapping = {
            "name": "name",
            "category": "category",
            "location": "location",
            "aliases": "aliases",
            "vernacular_name": "vernacular_name",
            "description": "description",
            "extra_metadata": "extra_metadata",
            "validation_status": "validation_status",
            "verified": "verified",
        }
        old_values: dict = {}
        new_values: dict = {}

        for field_name, value in changes.items():
            orm_field = field_mapping.get(field_name)
            if orm_field is None:
                continue
            if field_name == "location":
                old_geometry = await self.session.scalar(
                    select(func.ST_AsGeoJSON(PlaceORM.location)).where(
                        PlaceORM.id == place_id
                    )
                )
                old_values[field_name] = json.loads(old_geometry) if old_geometry else None
                setattr(place, orm_field, point_to_wkt(value))
            else:
                old_values[field_name] = getattr(place, orm_field)
                setattr(place, orm_field, value)
            new_values[field_name] = value

        await self.session.flush()
        self.session.add(
            PlaceHistoryORM(
                place_id=place_id,
                action="update",
                field_name=next(iter(new_values)) if len(new_values) == 1 else "multiple",
                old_value=old_values,
                new_value=new_values,
                changed_by=changed_by,
                note=note,
            )
        )
        await self.session.commit()
        await self.session.refresh(place)
        return place

    async def search(self, query: str) -> list[PlaceORM]:
        like_query = f"%{query}%"
        result = await self.session.execute(
            select(PlaceORM)
            .where(PlaceORM.name.ilike(like_query))
            .order_by(PlaceORM.id.desc())
        )
        places = list(result.scalars().all())
        if places:
            return places

        result = await self.session.execute(
            select(PlaceORM)
            .where(PlaceORM.vernacular_name.ilike(like_query))
            .order_by(PlaceORM.id.desc())
        )
        places = list(result.scalars().all())
        if places:
            return places

        result = await self.session.execute(select(PlaceORM).order_by(PlaceORM.id.desc()))
        all_places = list(result.scalars().all())
        normalized = query.lower()
        return [
            place
            for place in all_places
            if normalized in (place.vernacular_name or "").lower()
            or any(alias.lower().find(normalized) >= 0 for alias in place.aliases)
        ]

    async def set_validation_status(
        self,
        place_id: int,
        status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> PlaceORM | None:
        place = await self.get_by_id(place_id)
        if place is None:
            return None
        old_status = place.validation_status
        place.validation_status = status
        place.verified = status == "validated"
        await self.session.flush()
        self.session.add(
            PlaceHistoryORM(
                place_id=place_id,
                action="validate" if status == "validated" else "reject",
                field_name="validation_status",
                old_value={"validation_status": old_status},
                new_value={"validation_status": status},
                changed_by=changed_by,
                note=note,
            )
        )
        await self.session.commit()
        await self.session.refresh(place)
        return place

    async def list_history(self, place_id: int) -> list[PlaceHistoryORM]:
        result = await self.session.execute(
            select(PlaceHistoryORM).where(PlaceHistoryORM.place_id == place_id).order_by(PlaceHistoryORM.id.desc())
        )
        return list(result.scalars().all())
