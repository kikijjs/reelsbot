"""create jobs table

Revision ID: 0001
Revises:
Create Date: 2026-04-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE platform_enum AS ENUM ('instagram', 'youtube', 'tiktok')")
    op.execute(
        "CREATE TYPE job_status_enum AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')"
    )

    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("instagram_url", sa.Text, nullable=False),
        sa.Column(
            "platform",
            sa.Enum("instagram", "youtube", "tiktok", name="platform_enum"),
            nullable=False,
        ),
        # AI 분석 결과
        sa.Column("gemini_analysis", JSON, nullable=True),
        sa.Column("script", JSON, nullable=True),
        sa.Column("script_variant_b", JSON, nullable=True),
        # 미디어 경로
        sa.Column("downloaded_video_path", sa.Text, nullable=True),
        sa.Column("tts_audio_path", sa.Text, nullable=True),
        sa.Column("final_video_path", sa.Text, nullable=True),
        sa.Column("tts_voice", sa.String(100), nullable=True),
        # 예약 / 업로드
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        # 상태
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="job_status_enum"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        # 타임스탬프
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.execute("DROP TYPE job_status_enum")
    op.execute("DROP TYPE platform_enum")
