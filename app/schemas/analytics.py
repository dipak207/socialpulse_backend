"""Pydantic v2 schemas for analytics responses."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class PostMetrics(BaseModel):
    """Engagement metrics for a single post."""
    views: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    engagement_rate: float = Field(default=0.0, ge=0.0)
    virality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    trend_score: float = Field(default=0.0, ge=0.0, le=100.0)
    author_followers: Optional[int] = None


class PostMetadata(BaseModel):
    """Metadata for a post."""
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    author: str
    published_at: Optional[datetime] = None
    platform: str
    post_type: str
    url: str
    hashtags: list[str] = Field(default_factory=list)


class PostAnalysisResponse(BaseModel):
    """Full response for a single post analysis."""
    job_id: str
    status: str
    platform: str
    type: str
    url: str
    metadata: PostMetadata
    metrics: PostMetrics
    hashtags: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    data_source: str = "unknown"
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class TopPost(BaseModel):
    """Summary of a top-performing post for a profile."""
    url: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    virality_score: float = 0.0
    published_at: Optional[datetime] = None


class ProfileMetrics(BaseModel):
    """Aggregate metrics for a profile."""
    followers: int = 0
    following: Optional[int] = None
    posts_count: int = 0
    avg_engagement_rate: float = 0.0
    posting_frequency: float = 0.0  # posts per week
    verified: bool = False
    avg_views: int = 0
    avg_likes: int = 0
    avg_comments: int = 0
    avg_shares: int = 0


class ProfileAnalysisResponse(BaseModel):
    """Full response for a profile analysis."""
    job_id: str
    status: str
    platform: str
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    url: str
    metrics: ProfileMetrics
    top_posts: list[TopPost] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    data_source: str = "unknown"
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class CompareItem(BaseModel):
    """Single profile entry in a comparison response."""
    url: str
    platform: str
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    followers: int = 0
    avg_engagement_rate: float = 0.0
    posting_frequency: float = 0.0
    posts_count: int = 0
    top_posts: list[TopPost] = Field(default_factory=list)


class CompareResponse(BaseModel):
    """Response for multi-profile comparison."""
    job_id: str
    status: str
    profiles: list[CompareItem] = Field(default_factory=list)
    winner: Optional[str] = None  # username of the winner
    insights: list[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
