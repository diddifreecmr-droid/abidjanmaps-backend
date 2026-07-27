"""add journey analysis quality metrics

Revision ID: 20260727_0008
Revises: 20260727_0007
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "journey_analyses",
        sa.Column("moving_time_s", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "journey_analyses",
        sa.Column("stopped_time_s", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "journey_analyses",
        sa.Column("max_speed_kmh", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "journey_analyses",
        sa.Column("gps_gap_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "journey_analyses",
        sa.Column("suspicious_jump_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_journey_analyses_moving_time_s",
        "journey_analyses",
        "moving_time_s >= 0",
    )
    op.create_check_constraint(
        "ck_journey_analyses_stopped_time_s",
        "journey_analyses",
        "stopped_time_s >= 0",
    )
    op.create_check_constraint(
        "ck_journey_analyses_max_speed_kmh",
        "journey_analyses",
        "max_speed_kmh >= 0",
    )
    op.create_check_constraint(
        "ck_journey_analyses_gps_gap_count",
        "journey_analyses",
        "gps_gap_count >= 0",
    )
    op.create_check_constraint(
        "ck_journey_analyses_suspicious_jump_count",
        "journey_analyses",
        "suspicious_jump_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_journey_analyses_suspicious_jump_count",
        "journey_analyses",
        type_="check",
    )
    op.drop_constraint(
        "ck_journey_analyses_gps_gap_count",
        "journey_analyses",
        type_="check",
    )
    op.drop_constraint(
        "ck_journey_analyses_max_speed_kmh",
        "journey_analyses",
        type_="check",
    )
    op.drop_constraint(
        "ck_journey_analyses_stopped_time_s",
        "journey_analyses",
        type_="check",
    )
    op.drop_constraint(
        "ck_journey_analyses_moving_time_s",
        "journey_analyses",
        type_="check",
    )
    op.drop_column("journey_analyses", "suspicious_jump_count")
    op.drop_column("journey_analyses", "gps_gap_count")
    op.drop_column("journey_analyses", "max_speed_kmh")
    op.drop_column("journey_analyses", "stopped_time_s")
    op.drop_column("journey_analyses", "moving_time_s")
