"""add trigram and spatial search indexes

Revision ID: 20260825_0011
Revises: 20260727_0010
Create Date: 2026-08-25
"""

from alembic import op


revision = "20260825_0011"
down_revision = "20260727_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(
        "ix_places_name_trgm",
        "places",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_places_vernacular_name_trgm",
        "places",
        ["vernacular_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"vernacular_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_places_category_trgm",
        "places",
        ["category"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"category": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_roads_name_trgm",
        "roads",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    op.create_index(
        "ix_places_location_gist",
        "places",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_roads_geom_gist",
        "roads",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_route_reports_geometry_gist",
        "route_reports",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_route_reports_geometry_gist", table_name="route_reports")
    op.drop_index("ix_roads_geom_gist", table_name="roads")
    op.drop_index("ix_places_location_gist", table_name="places")
    op.drop_index("ix_roads_name_trgm", table_name="roads")
    op.drop_index("ix_places_category_trgm", table_name="places")
    op.drop_index("ix_places_vernacular_name_trgm", table_name="places")
    op.drop_index("ix_places_name_trgm", table_name="places")
