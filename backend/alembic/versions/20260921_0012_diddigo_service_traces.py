"""add DiddiGo service trace source fields

Revision ID: 20260921_0012
Revises: 20260825_0011
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260921_0012"
down_revision = "20260825_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("journeys", "user_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("journeys", sa.Column("source_service", sa.String(length=40), nullable=True))
    op.add_column("journeys", sa.Column("source_client_id", sa.String(length=80), nullable=True))
    op.add_column("journeys", sa.Column("source_ride_id", sa.String(length=80), nullable=True))
    op.create_index(
        "ix_journeys_source_service",
        "journeys",
        ["source_service"],
        unique=False,
    )
    op.create_index(
        "ix_journeys_source_ride_id",
        "journeys",
        ["source_ride_id"],
        unique=False,
    )
    op.create_index(
        "ix_journeys_source_service_ride_id",
        "journeys",
        ["source_service", "source_ride_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_journeys_source_service_ride_id", table_name="journeys")
    op.drop_index("ix_journeys_source_ride_id", table_name="journeys")
    op.drop_index("ix_journeys_source_service", table_name="journeys")
    op.drop_column("journeys", "source_ride_id")
    op.drop_column("journeys", "source_client_id")
    op.drop_column("journeys", "source_service")
    op.alter_column("journeys", "user_id", existing_type=sa.Integer(), nullable=False)
