"""add map trace insights

Revision ID: 20260727_0007
Revises: 20260727_0006
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260727_0007"
down_revision = "20260727_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "map_trace_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("journey_id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("insight_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("geometry", JSONB, nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'validated', 'rejected')",
            name="ck_map_trace_insights_status",
        ),
        sa.CheckConstraint(
            "severity >= 1 AND severity <= 5",
            name="ck_map_trace_insights_severity",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_map_trace_insights_confidence_score",
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["journey_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_map_trace_insights_analysis_id",
        "map_trace_insights",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        "ix_map_trace_insights_insight_type",
        "map_trace_insights",
        ["insight_type"],
        unique=False,
    )
    op.create_index(
        "ix_map_trace_insights_journey_id",
        "map_trace_insights",
        ["journey_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_map_trace_insights_journey_id", table_name="map_trace_insights")
    op.drop_index("ix_map_trace_insights_insight_type", table_name="map_trace_insights")
    op.drop_index("ix_map_trace_insights_analysis_id", table_name="map_trace_insights")
    op.drop_table("map_trace_insights")
