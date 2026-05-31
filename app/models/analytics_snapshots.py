"""SQLAlchemy model for analytics snapshots (time-series data per profile)."""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    BigInteger,
    Integer,
    Numeric,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AnalyticsSnapshot(Base):
    """Daily analytics snapshot for a profile."""

    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyzed_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    followers: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(
        Numeric(8, 4), default=0.0, nullable=False
    )
    posts_published: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "snapshot_date", name="uq_profile_snapshot_date"),
        Index("ix_analytics_snapshots_profile_date", "profile_id", "snapshot_date"),
    )

    def __repr__(self) -> str:
        return f"<AnalyticsSnapshot profile={self.profile_id} date={self.snapshot_date}>"
