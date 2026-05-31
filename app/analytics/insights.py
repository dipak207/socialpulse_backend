"""AI-driven human-readable insights generator for posts and profiles."""
from datetime import datetime, timezone
from typing import Optional


class InsightsGenerator:
    """
    Generates emoji-prefixed, human-readable insight strings
    from computed analytics metrics.
    """

    # ---- Post insight thresholds ----
    def for_post(
        self,
        platform: str,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        engagement_rate: float,
        virality_score: float,
        followers: int,
        published_at: Optional[datetime] = None,
    ) -> list[str]:
        """
        Generate 3-5 insights for a single post.

        Args:
            platform: Platform name (youtube, instagram, twitter, tiktok, linkedin).
            views, likes, comments, shares: Raw engagement counts.
            engagement_rate: Computed ER percentage.
            virality_score: Computed virality score [0, 100].
            followers: Author's follower count.
            published_at: Post publication datetime (UTC).

        Returns:
            List of emoji-prefixed insight strings.
        """
        insights: list[str] = []

        # --- Virality insight ---
        if virality_score >= 80:
            insights.append(
                "🚀 This content is going viral! Virality score is exceptionally high — "
                "strong shares, comments, and engagement are driving explosive reach."
            )
        elif virality_score >= 60:
            insights.append(
                "📈 Strong viral potential detected. This post is gaining significant "
                "traction across the platform."
            )
        elif virality_score >= 40:
            insights.append(
                "⚡ Moderate viral momentum. The content is performing above average "
                "and has room to grow with promotion."
            )
        else:
            insights.append(
                "📊 Below-average viral score. Consider boosting with paid promotion "
                "or repurposing for other platforms."
            )

        # --- Engagement rate insight ---
        if engagement_rate >= 10.0:
            insights.append(
                f"🔥 Outstanding engagement rate of {engagement_rate:.2f}% — "
                "top 1% of creators on this platform!"
            )
        elif engagement_rate >= 5.0:
            insights.append(
                f"✅ Excellent engagement rate of {engagement_rate:.2f}% — "
                "well above the platform average of ~2-3%."
            )
        elif engagement_rate >= 2.0:
            insights.append(
                f"👍 Healthy engagement rate of {engagement_rate:.2f}%. "
                "Consistent with top-performing content in this niche."
            )
        else:
            insights.append(
                f"⚠️ Low engagement rate of {engagement_rate:.2f}%. "
                "Try more interactive content (polls, questions) to boost engagement."
            )

        # --- Comment-to-like ratio (community signal) ---
        if likes > 0:
            comment_ratio = comments / max(likes, 1)
            if comment_ratio >= 0.1:
                insights.append(
                    "💬 High comment-to-like ratio — this post is sparking real "
                    "conversations. Community engagement is strong."
                )

        # --- Share insight ---
        if shares > 0 and views > 0:
            share_pct = shares / max(views, 1) * 100
            if share_pct >= 5:
                insights.append(
                    f"📤 Impressive share rate of {share_pct:.1f}% — "
                    "audiences are actively recommending this content."
                )

        # --- Recency insight ---
        if published_at:
            now = datetime.now(timezone.utc)
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            hours_old = (now - published_at).total_seconds() / 3600.0
            if hours_old <= 24:
                insights.append(
                    "⏱️ Published within the last 24 hours — engagement is still "
                    "ramping up. Expect metrics to climb further."
                )

        # --- Platform-specific tips ---
        platform_tips = {
            "youtube": "🎯 Tip: Add chapters and timestamps to increase average view duration.",
            "instagram": "🎯 Tip: Use 5-10 targeted hashtags in the first comment to boost discoverability.",
            "twitter": "🎯 Tip: Retweet from secondary accounts and engage with top replies to boost reach.",
            "tiktok": "🎯 Tip: Post at peak hours (6-10 PM local) and use trending sounds to maximize FYP placement.",
            "linkedin": "🎯 Tip: Tag relevant people and companies to extend organic reach on LinkedIn.",
        }
        tip = platform_tips.get(platform.lower())
        if tip:
            insights.append(tip)

        return insights[:5]  # Return at most 5 insights

    def for_profile(
        self,
        platform: str,
        followers: int,
        avg_engagement_rate: float,
        posting_frequency: float,
        posts_count: int,
    ) -> list[str]:
        """
        Generate 3-5 insights for a social media profile.

        Args:
            platform: Platform name.
            followers: Total follower count.
            avg_engagement_rate: Average ER across recent posts.
            posting_frequency: Posts per week.
            posts_count: Total post count.

        Returns:
            List of emoji-prefixed insight strings.
        """
        insights: list[str] = []

        # --- Follower tier ---
        if followers >= 1_000_000:
            insights.append(
                f"🌟 Mega-influencer with {followers:,} followers — "
                "brand partnerships will command premium rates."
            )
        elif followers >= 100_000:
            insights.append(
                f"⭐ Macro-influencer with {followers:,} followers — "
                "strong brand deal potential with broad audience reach."
            )
        elif followers >= 10_000:
            insights.append(
                f"📣 Micro-influencer with {followers:,} followers — "
                "typically delivers higher engagement rates for niche brands."
            )
        else:
            insights.append(
                f"🌱 Nano-influencer with {followers:,} followers — "
                "authentic community connection with highly engaged niche audience."
            )

        # --- Engagement rate ---
        if avg_engagement_rate >= 6.0:
            insights.append(
                f"🔥 Exceptional average engagement rate of {avg_engagement_rate:.2f}% — "
                "this creator's audience is highly active and loyal."
            )
        elif avg_engagement_rate >= 3.0:
            insights.append(
                f"✅ Strong average engagement rate of {avg_engagement_rate:.2f}% — "
                "above platform average, indicating quality content."
            )
        elif avg_engagement_rate >= 1.0:
            insights.append(
                f"📊 Average engagement rate of {avg_engagement_rate:.2f}%. "
                "Content resonates with followers but has room to grow."
            )
        else:
            insights.append(
                f"⚠️ Low average engagement rate of {avg_engagement_rate:.2f}%. "
                "Audience may not be closely aligned with content niche."
            )

        # --- Posting frequency ---
        if posting_frequency >= 7:
            insights.append(
                f"📅 Very high posting frequency of {posting_frequency:.1f} posts/week — "
                "excellent for algorithm visibility but watch for quality consistency."
            )
        elif posting_frequency >= 3:
            insights.append(
                f"📅 Consistent posting cadence of {posting_frequency:.1f} posts/week — "
                "ideal for maintaining algorithmic momentum."
            )
        elif posting_frequency >= 1:
            insights.append(
                f"📅 Moderate posting frequency of {posting_frequency:.1f} posts/week. "
                "Increasing to 3-5 posts/week could significantly boost reach."
            )
        else:
            insights.append(
                "📅 Low posting frequency — irregular posting may hurt algorithmic reach. "
                "Consistency is key to sustained growth."
            )

        # --- Content volume ---
        if posts_count >= 500:
            insights.append(
                f"📚 Extensive content library with {posts_count:,} posts — "
                "strong SEO signal and long-term discoverability."
            )
        elif posts_count >= 100:
            insights.append(
                f"📚 Solid content library of {posts_count:,} posts — "
                "good foundation for algorithmic recommendations."
            )

        return insights[:5]

    def for_comparison(self, profiles: list[dict]) -> list[str]:
        """
        Generate comparative insights for multiple profiles.

        Args:
            profiles: List of profile dicts, each containing:
                - username, followers, avg_engagement_rate, posting_frequency

        Returns:
            List of emoji-prefixed comparison insight strings.
        """
        if not profiles:
            return []
        insights: list[str] = []

        # Rank by engagement rate
        by_er = sorted(profiles, key=lambda p: p.get("avg_engagement_rate", 0), reverse=True)
        top_er = by_er[0]
        insights.append(
            f"🏆 **@{top_er.get('username', 'N/A')}** leads in engagement rate "
            f"at {top_er.get('avg_engagement_rate', 0):.2f}% — "
            "indicating the most active and loyal audience."
        )

        # Rank by followers
        by_followers = sorted(profiles, key=lambda p: p.get("followers", 0), reverse=True)
        top_followers = by_followers[0]
        if top_followers.get("username") != top_er.get("username"):
            insights.append(
                f"📣 **@{top_followers.get('username', 'N/A')}** has the largest audience "
                f"with {top_followers.get('followers', 0):,} followers — "
                "best for broad brand awareness campaigns."
            )

        # Posting frequency leader
        by_freq = sorted(profiles, key=lambda p: p.get("posting_frequency", 0), reverse=True)
        top_freq = by_freq[0]
        insights.append(
            f"📅 **@{top_freq.get('username', 'N/A')}** posts most frequently at "
            f"{top_freq.get('posting_frequency', 0):.1f}x/week — "
            "highest algorithmic exposure."
        )

        # Engagement vs. follower count analysis
        if len(profiles) >= 2:
            low_followers_high_er = [
                p for p in profiles
                if p.get("followers", 0) < 50_000 and p.get("avg_engagement_rate", 0) >= 5.0
            ]
            if low_followers_high_er:
                usernames = ", ".join(
                    f"@{p.get('username', 'N/A')}" for p in low_followers_high_er
                )
                insights.append(
                    f"💡 {usernames} show{'s' if len(low_followers_high_er) == 1 else ''} "
                    "high engagement despite smaller followings — "
                    "ideal for niche influencer marketing with strong ROI."
                )

        insights.append(
            "📊 Tip: For brand partnerships, prioritize creators with ER > 3% over "
            "raw follower counts for better campaign performance."
        )

        return insights[:5]


# Singleton instance
insights_generator = InsightsGenerator()

__all__ = ["InsightsGenerator", "insights_generator"]
