"""SQLAlchemy model for trending hashtags across platforms."""
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    Numeric,
    DateTime,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class HashtagTrend(Base):
    """Tracks hashtag usage and engagement across platforms."""

    __tablename__ = "hashtag_trends"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hashtag: Mapped[str] = mapped_column(String(256), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    avg_engagement_rate: Mapped[float] = mapped_column(
        Numeric(8, 4), default=0.0, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("hashtag", "platform", name="uq_hashtag_platform"),
        Index("ix_hashtag_trends_platform_count", "platform", "occurrence_count"),
        Index("ix_hashtag_trends_hashtag", "hashtag"),
    )

    def __repr__(self) -> str:
        return f"<HashtagTrend #{self.hashtag} on {self.platform}>"
