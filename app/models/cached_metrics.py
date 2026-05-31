"""SQLAlchemy model for cached API/scrape results."""
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    JSON,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CachedMetric(Base):
    """Stores cached scraping / API results with TTL."""

    __tablename__ = "cached_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cache_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_cached_metrics_cache_key", "cache_key"),
        Index("ix_cached_metrics_expires_at", "expires_at"),
        Index("ix_cached_metrics_platform", "platform"),
    )

    def __repr__(self) -> str:
        return f"<CachedMetric key={self.cache_key[:40]}>"
