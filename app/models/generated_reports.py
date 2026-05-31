"""SQLAlchemy model for generated analytics reports."""
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class GeneratedReport(Base):
    """Tracks generated export reports (JSON, CSV, PDF)."""

    __tablename__ = "generated_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # e.g. "post", "profile", "compare"
    format: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # "json" | "csv" | "pdf"
    subject_urls: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False, default="30d")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # "pending" | "completed" | "failed"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_generated_reports_status", "status"),
        Index("ix_generated_reports_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<GeneratedReport {self.report_type}/{self.format} status={self.status}>"
