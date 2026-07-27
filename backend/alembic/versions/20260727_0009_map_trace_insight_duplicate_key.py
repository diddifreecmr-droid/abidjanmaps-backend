"""add map trace insight duplicate key

Revision ID: 20260727_0009
Revises: 20260727_0008
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0009"
down_revision = "20260727_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "map_trace_insights",
        sa.Column("duplicate_key", sa.String(length=160), nullable=True),
    )
    op.create_index(
        "ix_map_trace_insights_duplicate_key",
        "map_trace_insights",
        ["duplicate_key"],
        unique=False,
    )
    op.create_index(
        "uq_map_trace_insights_active_duplicate_key",
        "map_trace_insights",
        ["duplicate_key"],
        unique=True,
        postgresql_where=sa.text("duplicate_key IS NOT NULL AND status IN ('proposed', 'validated')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_map_trace_insights_active_duplicate_key",
        table_name="map_trace_insights",
    )
    op.drop_index("ix_map_trace_insights_duplicate_key", table_name="map_trace_insights")
    op.drop_column("map_trace_insights", "duplicate_key")
