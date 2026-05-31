"""SQLAlchemy model for analyzed social media profiles."""
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    Boolean,
    BigInteger,
    Integer,
    Numeric,
    DateTime,
    JSON,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AnalyzedProfile(Base):
    """Stores analyzed social media profile data."""

    __tablename__ = "analyzed_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(256), nullable=False)
    username: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    followers: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    following: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    posts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_engagement_rate: Mapped[float] = mapped_column(
        Numeric(8, 4), default=0.0, nullable=False
    )
    posting_frequency: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.0, nullable=False
    )
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    last_analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
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
        Index("ix_analyzed_profiles_platform_username", "platform", "username"),
        Index("ix_analyzed_profiles_platform_user_id", "platform", "platform_user_id"),
    )

    def __repr__(self) -> str:
        return f"<AnalyzedProfile {self.platform}/@{self.username}>"
