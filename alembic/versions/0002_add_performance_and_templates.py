"""add performance_metrics and script_templates tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "performance_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("interval_hours", sa.Integer, nullable=False),
        sa.Column("views", sa.BigInteger, default=0),
        sa.Column("likes", sa.Integer, default=0),
        sa.Column("comments", sa.Integer, default=0),
        sa.Column("shares", sa.Integer, default=0),
    )
    op.create_index("ix_perf_job_id", "performance_metrics", ["job_id"])

    op.create_table(
        "script_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("script", JSON, nullable=False),
        sa.Column("source_job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("performance_score", sa.Float, default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_template_score", "script_templates", ["performance_score"])


def downgrade() -> None:
    op.drop_table("script_templates")
    op.drop_table("performance_metrics")
