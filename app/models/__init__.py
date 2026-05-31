"""Models package — imports all models so Alembic can auto-discover them."""
from app.models.analyzed_profiles import AnalyzedProfile
from app.models.analyzed_posts import AnalyzedPost
from app.models.analytics_snapshots import AnalyticsSnapshot
from app.models.hashtag_trends import HashtagTrend
from app.models.cached_metrics import CachedMetric
from app.models.generated_reports import GeneratedReport

__all__ = [
    "AnalyzedProfile",
    "AnalyzedPost",
    "AnalyticsSnapshot",
    "HashtagTrend",
    "CachedMetric",
    "GeneratedReport",
]
