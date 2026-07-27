"""add map trace insight evidence counters

Revision ID: 20260727_0010
Revises: 20260727_0009
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0010"
down_revision = "20260727_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "map_trace_insights",
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "map_trace_insights",
        sa.Column("latest_evidence_trace_id", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_map_trace_insights_evidence_count",
        "map_trace_insights",
        "evidence_count >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_map_trace_insights_evidence_count",
        "map_trace_insights",
        type_="check",
    )
    op.drop_column("map_trace_insights", "latest_evidence_trace_id")
    op.drop_column("map_trace_insights", "evidence_count")
