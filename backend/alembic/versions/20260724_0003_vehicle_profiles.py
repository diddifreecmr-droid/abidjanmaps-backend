"""add allowed vehicle profiles to roads

Revision ID: 20260724_0003
Revises: 20260724_0002
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


revision = "20260724_0003"
down_revision = "20260724_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roads",
        sa.Column(
            "allowed_vehicle_profiles",
            ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text(
                "ARRAY['car', 'motorcycle', 'truck']::varchar[]"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("roads", "allowed_vehicle_profiles")
