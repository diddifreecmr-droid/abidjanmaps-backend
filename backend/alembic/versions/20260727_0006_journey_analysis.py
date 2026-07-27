"""add journey analysis table

Revision ID: 20260727_0006
Revises: 20260727_0005
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260727_0006"
down_revision = "20260727_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journey_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("journey_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("points_count", sa.Integer(), nullable=False),
        sa.Column("usable_points_count", sa.Integer(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("quality_label", sa.String(length=20), nullable=False),
        sa.Column("actual_distance_m", sa.Float(), nullable=False),
        sa.Column("actual_duration_s", sa.Integer(), nullable=False),
        sa.Column("average_speed_kmh", sa.Float(), nullable=False),
        sa.Column("phone_average_speed_kmh", sa.Float(), nullable=True),
        sa.Column("planned_distance_m", sa.Integer(), nullable=True),
        sa.Column("planned_duration_s", sa.Integer(), nullable=True),
        sa.Column("distance_delta_m", sa.Float(), nullable=True),
        sa.Column("duration_delta_s", sa.Integer(), nullable=True),
        sa.Column("duration_ratio", sa.Float(), nullable=True),
        sa.Column("detected_events", JSONB, nullable=False),
        sa.Column("recommendation", sa.String(length=40), nullable=False),
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
            "status IN ('analyzed')",
            name="ck_journey_analyses_status",
        ),
        sa.CheckConstraint(
            "quality_score >= 0 AND quality_score <= 1",
            name="ck_journey_analyses_quality_score",
        ),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("journey_id", name="uq_journey_analyses_journey_id"),
    )
    op.create_index(
        "ix_journey_analyses_journey_id",
        "journey_analyses",
        ["journey_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_journey_analyses_journey_id", table_name="journey_analyses")
    op.drop_table("journey_analyses")
