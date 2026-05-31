"""Core analytics computation engine for SocialPulse Intelligence."""
import math
from datetime import datetime, timezone
from typing import Optional


class AnalyticsEngine:
    """
    Stateless analytics computation engine.

    All methods are pure functions that take raw metrics
    and return computed scores / rates.
    """

    def engagement_rate(
        self,
        likes: int,
        comments: int,
        shares: int,
        followers: int,
    ) -> float:
        """
        Compute engagement rate as a percentage.

        Formula: (likes + comments + shares) / followers * 100

        Returns 0.0 if followers is zero or negative.
        """
        if followers <= 0:
            return 0.0
        er = (likes + comments + shares) / followers * 100.0
        return round(er, 4)

    def virality_score(
        self,
        likes: int,
        comments: int,
        shares: int,
        views: int,
        followers: int,
        published_at: Optional[datetime] = None,
    ) -> float:
        """
        Compute a composite virality score in the range [0, 100].

        Components:
          - ER component     (40%): engagement rate vs. 5% benchmark
          - Share ratio      (25%): shares / views ratio vs. 2% benchmark
          - Comment ratio    (15%): comments / views ratio vs. 1% benchmark
          - Like/view ratio  (10%): likes / views ratio vs. 10% benchmark
          - Recency decay    (10%): bonus for content published within 48h
        """
        # Guard against zeros
        views_safe = max(views, 1)
        followers_safe = max(followers, 1)

        # 1. Engagement rate component (0-40 pts)
        er = self.engagement_rate(likes, comments, shares, followers_safe)
        er_score = min(er / 5.0, 1.0) * 40.0

        # 2. Share ratio (0-25 pts)
        share_ratio = shares / views_safe
        share_score = min(share_ratio / 0.02, 1.0) * 25.0

        # 3. Comment ratio (0-15 pts)
        comment_ratio = comments / views_safe
        comment_score = min(comment_ratio / 0.01, 1.0) * 15.0

        # 4. Like/view ratio (0-10 pts)
        like_ratio = likes / views_safe
        like_score = min(like_ratio / 0.10, 1.0) * 10.0

        # 5. Recency bonus (0-10 pts)
        recency_score = 0.0
        if published_at:
            now = datetime.now(timezone.utc)
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            hours_old = (now - published_at).total_seconds() / 3600.0
            if hours_old <= 24:
                recency_score = 10.0
            elif hours_old <= 48:
                recency_score = 5.0
            elif hours_old <= 168:  # 1 week
                recency_score = 2.0

        total = er_score + share_score + comment_score + like_score + recency_score
        return round(min(total, 100.0), 2)

    def trend_score(
        self, current_er: float, previous_ers: list[float]
    ) -> float:
        """
        Compute a trend momentum score in the range [0, 100].

        Compares current engagement rate against historical average.
        A score of 50 = no change; >50 = growing; <50 = declining.

        Args:
            current_er: Current engagement rate.
            previous_ers: List of previous engagement rates (oldest first).
        """
        if not previous_ers:
            return 50.0
        avg_previous = sum(previous_ers) / len(previous_ers)
        if avg_previous == 0:
            return 75.0 if current_er > 0 else 50.0
        ratio = current_er / avg_previous
        # Map ratio to 0-100 using sigmoid-like curve centered at 1.0
        score = 50.0 * ratio  # Linear approximation
        return round(min(max(score, 0.0), 100.0), 2)

    def post_performance_score(
        self,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        platform_avg_er: float = 3.0,
    ) -> float:
        """
        Score a post's performance relative to a platform average ER.

        Returns a score in [0, 100].
        """
        views_safe = max(views, 1)
        er = (likes + comments + shares) / views_safe * 100.0
        relative = er / max(platform_avg_er, 0.01)
        score = min(relative * 50.0, 100.0)
        return round(score, 2)

    def engagement_velocity(
        self, current: int, previous: int, hours_elapsed: float
    ) -> float:
        """
        Compute engagement velocity: change in interactions per hour.

        Args:
            current: Current total engagement count.
            previous: Previous total engagement count.
            hours_elapsed: Time between measurements in hours.

        Returns:
            Interactions gained per hour.
        """
        if hours_elapsed <= 0:
            return 0.0
        delta = max(current - previous, 0)
        return round(delta / hours_elapsed, 2)

    def posting_frequency(self, post_dates: list[datetime]) -> float:
        """
        Calculate posting frequency in posts per week.

        Args:
            post_dates: List of post publication datetimes.

        Returns:
            Posts per week (float).
        """
        if len(post_dates) < 2:
            return float(len(post_dates))

        sorted_dates = sorted(post_dates)
        first = sorted_dates[0]
        last = sorted_dates[-1]

        if first.tzinfo is None:
            first = first.replace(tzinfo=timezone.utc)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

        total_days = (last - first).total_seconds() / 86400.0
        if total_days < 1:
            return float(len(post_dates))

        weeks = total_days / 7.0
        frequency = len(post_dates) / weeks
        return round(frequency, 2)

    def hashtag_score(
        self, hashtag: str, frequency: int, avg_engagement_rate: float
    ) -> float:
        """
        Compute a hashtag relevance score based on usage and engagement.

        Returns a score in [0, 100].
        """
        freq_score = min(math.log1p(frequency) / math.log1p(1000), 1.0) * 50.0
        er_score = min(avg_engagement_rate / 10.0, 1.0) * 50.0
        return round(freq_score + er_score, 2)

    def growth_rate(self, current: float, previous: float) -> float:
        """
        Compute percentage growth rate between two values.

        Args:
            current: Current metric value.
            previous: Previous metric value.

        Returns:
            Percentage change (positive = growth, negative = decline).
        """
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        rate = (current - previous) / abs(previous) * 100.0
        return round(rate, 2)


# Singleton instance
analytics_engine = AnalyticsEngine()

__all__ = ["AnalyticsEngine", "analytics_engine"]
