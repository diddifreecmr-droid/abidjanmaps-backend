"""initial schema

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import ARRAY, JSONB


revision = "20260724_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The backend schema stores PostGIS geometry types from its first revision.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "roads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("geom", Geometry("LINESTRING", srid=4326), nullable=False),
        sa.Column("surface_state", sa.String(length=80), nullable=False),
        sa.Column("seasonal_practicability", sa.String(length=80), nullable=False),
        sa.Column("surface_reel", sa.String(length=80), nullable=True),
        sa.Column("tonnage_max_reel_t", sa.Float(), nullable=True),
        sa.Column("point_controle", sa.String(length=80), nullable=True),
        sa.Column("temps_attente_p50_s", sa.Integer(), nullable=True),
        sa.Column("temps_attente_p90_s", sa.Integer(), nullable=True),
        sa.Column("eclairage", sa.Integer(), nullable=True),
        sa.Column("securite_nuit", sa.Integer(), nullable=True),
        sa.Column("width_usable_m", sa.Float(), nullable=True),
        sa.Column("pente_max_pct", sa.Float(), nullable=True),
        sa.Column("type_flux", sa.String(length=80), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("validation_status", sa.String(length=20), nullable=False, server_default=sa.text("'proposed'")),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_roads_name"), "roads", ["name"], unique=False)

    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("location", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("aliases", ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("vernacular_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("validation_status", sa.String(length=20), nullable=False, server_default=sa.text("'proposed'")),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_places_name"), "places", ["name"], unique=False)
    op.create_index(op.f("ix_places_category"), "places", ["category"], unique=False)
    op.create_index(op.f("ix_places_vernacular_name"), "places", ["vernacular_name"], unique=False)

    op.create_table(
        "route_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("road_id", sa.Integer(), sa.ForeignKey("roads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("report_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("geometry", Geometry("POINT", srid=4326), nullable=True),
        sa.Column("reported_by", sa.String(length=120), nullable=True),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_route_reports_report_type"), "route_reports", ["report_type"], unique=False)

    op.create_table(
        "road_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("road_id", sa.Integer(), sa.ForeignKey("roads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("changed_by", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_road_history_road_id"), "road_history", ["road_id"], unique=False)

    op.create_table(
        "place_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("changed_by", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_place_history_place_id"), "place_history", ["place_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_place_history_place_id"), table_name="place_history")
    op.drop_table("place_history")
    op.drop_index(op.f("ix_road_history_road_id"), table_name="road_history")
    op.drop_table("road_history")
    op.drop_index(op.f("ix_route_reports_report_type"), table_name="route_reports")
    op.drop_table("route_reports")
    op.drop_index(op.f("ix_places_vernacular_name"), table_name="places")
    op.drop_index(op.f("ix_places_category"), table_name="places")
    op.drop_index(op.f("ix_places_name"), table_name="places")
    op.drop_table("places")
    op.drop_index(op.f("ix_roads_name"), table_name="roads")
    op.drop_table("roads")
