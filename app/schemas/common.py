"""Common Pydantic schemas for requests and shared responses."""
from pydantic import BaseModel, field_validator
from typing import Optional


class URLRequest(BaseModel):
    """Request model for single URL analysis."""
    url: str
    timeframe: Optional[str] = "30d"

    @field_validator("url")
    @classmethod
    def url_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("URL must not be empty.")
        return v.strip()

    @field_validator("timeframe")
    @classmethod
    def valid_timeframe(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"7d", "14d", "30d", "90d", "180d", "365d", "all"}
        if v and v not in allowed:
            raise ValueError(f"timeframe must be one of {allowed}")
        return v


class CompareRequest(BaseModel):
    """Request model for multi-URL comparison."""
    urls: list[str]
    timeframe: Optional[str] = "30d"

    @field_validator("urls")
    @classmethod
    def validate_urls_count(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("At least 2 URLs are required for comparison.")
        if len(v) > 5:
            raise ValueError("Maximum 5 URLs allowed for comparison.")
        return [u.strip() for u in v if u.strip()]


class DetectResponse(BaseModel):
    """Response for platform detection."""
    platform: str
    type: str
    identifier: str
    display_url: str


class JobResponse(BaseModel):
    """Response when a background analysis job is submitted."""
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response for job status polling."""
    job_id: str
    status: str  # submitted | fetching | computing | completed | failed
    progress: int  # 0-100
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None
