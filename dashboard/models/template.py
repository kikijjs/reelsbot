import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dashboard.db import Base


class ScriptTemplate(Base):
    __tablename__ = "script_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    script: Mapped[dict] = mapped_column(JSON, nullable=False)       # Script5Parts JSON
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    performance_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ScriptTemplate name={self.name} score={self.performance_score}>"
