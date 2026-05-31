"""SQLAlchemy model for analyzed social media posts."""
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    BigInteger,
    Numeric,
    DateTime,
    JSON,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AnalyzedPost(Base):
    """Stores analyzed social media post data."""

    __tablename__ = "analyzed_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_post_id: Mapped[str] = mapped_column(String(256), nullable=False)
    post_type: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(256), nullable=False)
    author_followers: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(
        Numeric(8, 4), default=0.0, nullable=False
    )
    virality_score: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.0, nullable=False
    )
    trend_score: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.0, nullable=False
    )
    hashtags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_analyzed_posts_platform_post_id", "platform", "platform_post_id"),
        Index("ix_analyzed_posts_author", "author"),
        Index("ix_analyzed_posts_virality_score", "virality_score"),
        Index("ix_analyzed_posts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AnalyzedPost {self.platform}/{self.platform_post_id}>"
