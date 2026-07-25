"""add route report validation workflow

Revision ID: 20260724_0002
Revises: 00f7654f2505
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260724_0002"
down_revision = "00f7654f2505"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "route_reports",
        sa.Column(
            "validation_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'proposed'"),
        ),
    )
    op.add_column(
        "route_reports",
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "route_reports",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "route_reports",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        op.f("ix_route_reports_validation_status"),
        "route_reports",
        ["validation_status"],
        unique=False,
    )

    op.create_table(
        "route_report_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "route_report_id",
            sa.Integer(),
            sa.ForeignKey("route_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("changed_by", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        op.f("ix_route_report_history_route_report_id"),
        "route_report_history",
        ["route_report_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_route_report_history_route_report_id"),
        table_name="route_report_history",
    )
    op.drop_table("route_report_history")
    op.drop_index(
        op.f("ix_route_reports_validation_status"),
        table_name="route_reports",
    )
    op.drop_column("route_reports", "updated_at")
    op.drop_column("route_reports", "reviewed_at")
    op.drop_column("route_reports", "reviewed_by")
    op.drop_column("route_reports", "validation_status")
