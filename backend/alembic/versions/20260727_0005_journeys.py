"""add journey collection tables

Revision ID: 20260727_0005
Revises: 20260724_0004
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260727_0005"
down_revision = "20260724_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journeys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("profile", sa.String(length=30), nullable=False),
        sa.Column("start_location", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("end_location", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("planned_distance_m", sa.Integer(), nullable=True),
        sa.Column("planned_duration_s", sa.Integer(), nullable=True),
        sa.Column("planned_route_geometry", JSONB, nullable=True),
        sa.Column("actual_distance_m", sa.Float(), nullable=True),
        sa.Column("actual_duration_s", sa.Integer(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('started', 'finished', 'cancelled')",
            name="ck_journeys_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_journeys_user_id", "journeys", ["user_id"], unique=False)

    op.create_table(
        "journey_positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("journey_id", sa.Integer(), nullable=False),
        sa.Column("location", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("speed_mps", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journey_positions_journey_id",
        "journey_positions",
        ["journey_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_journey_positions_journey_id", table_name="journey_positions")
    op.drop_table("journey_positions")
    op.drop_index("ix_journeys_user_id", table_name="journeys")
    op.drop_table("journeys")
