from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.persistence.base import Base


class RoadORM(Base):
    __tablename__ = "roads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    geom: Mapped[str] = mapped_column(Geometry("LINESTRING", srid=4326), nullable=False)
    surface_state: Mapped[str] = mapped_column(String(80), nullable=False)
    seasonal_practicability: Mapped[str] = mapped_column(String(80), nullable=False)
    surface_reel: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tonnage_max_reel_t: Mapped[float | None] = mapped_column(Float, nullable=True)
    point_controle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    temps_attente_p50_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temps_attente_p90_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eclairage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    securite_nuit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width_usable_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    pente_max_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    type_flux: Mapped[str | None] = mapped_column(String(80), nullable=True)
    allowed_vehicle_profiles: Mapped[list[str]] = mapped_column(
        ARRAY(String()),
        nullable=False,
        default=lambda: ["car", "motorcycle", "truck"],
        server_default=text("ARRAY['car', 'motorcycle', 'truck']::varchar[]"),
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    extra_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlaceORM(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    location: Mapped[str] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False, default=list)
    vernacular_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    extra_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RoadHistoryORM(Base):
    __tablename__ = "road_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    road_id: Mapped[int] = mapped_column(
        ForeignKey("roads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlaceHistoryORM(Base):
    __tablename__ = "place_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_id: Mapped[int] = mapped_column(
        ForeignKey("places.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
