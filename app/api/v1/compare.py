"""API routes: POST /compare, GET /compare/{job_id} — multi-profile comparison."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from app.schemas.common import CompareRequest, JobResponse, JobStatusResponse
from app.services.analysis_service import create_job_id, ADAPTERS, detector
from app.services.cache_service import (
    set_job_status,
    get_job_status,
    get_cached,
    set_cached,
    make_cache_key,
)
from app.analytics.insights import insights_generator
from app.utils.rate_limiter import limiter
from app.utils.logger import logger

router = APIRouter()


async def _run_comparison(job_id: str, urls: list[str]) -> None:
    """
    Background task that fetches each profile and builds a comparison payload.

    Args:
        job_id: Unique job identifier.
        urls: List of 2-5 profile URLs to compare.
    """
    try:
        await set_job_status(
            job_id, "fetching", 10, f"Starting comparison of {len(urls)} profiles..."
        )

        profiles: list[dict] = []
        total = len(urls)

        for idx, url in enumerate(urls, start=1):
            progress = 10 + int((idx / total) * 65)
            await set_job_status(
                job_id,
                "fetching",
                progress,
                f"Fetching profile {idx}/{total}: {url[:50]}...",
            )

            try:
                # Detect platform
                detection = detector.detect(url)
                platform = detection["platform"]
                identifier = detection["identifier"]

                # Check cache first
                cache_key = make_cache_key("profile", platform, identifier)
                cached = await get_cached(cache_key)

                if cached:
                    raw = cached
                    logger.info("Compare: cache hit for %s/%s", platform, identifier)
                else:
                    adapter = ADAPTERS.get(platform)
                    if not adapter:
                        raise ValueError(f"No adapter for platform: {platform}")
                    raw = await adapter.fetch_profile(identifier)
                    await set_cached(cache_key, raw, ttl_seconds=1800)

                profiles.append(
                    {
                        "url": url,
                        "platform": platform,
                        "username": raw.get("username", identifier),
                        "display_name": raw.get("display_name"),
                        "avatar_url": raw.get("avatar_url"),
                        "followers": raw.get("followers", 0),
                        "avg_engagement_rate": raw.get("avg_engagement_rate", 0.0),
                        "posting_frequency": raw.get("posting_frequency", 0.0),
                        "posts_count": raw.get("posts_count", 0),
                        "top_posts": raw.get("top_posts", [])[:5],
                    }
                )
            except Exception as exc:
                logger.warning("Failed to fetch profile for %s: %s", url, exc)
                profiles.append(
                    {
                        "url": url,
                        "platform": "unknown",
                        "username": url,
                        "error": str(exc),
                        "followers": 0,
                        "avg_engagement_rate": 0.0,
                        "posting_frequency": 0.0,
                        "posts_count": 0,
                        "top_posts": [],
                    }
                )

        # Generate comparison insights
        await set_job_status(job_id, "computing", 80, "Generating comparison insights...")
        comparison_insights = insights_generator.for_comparison(profiles)

        # Determine winner by engagement rate
        valid_profiles = [p for p in profiles if "error" not in p]
        winner = None
        if valid_profiles:
            best = max(valid_profiles, key=lambda p: p.get("avg_engagement_rate", 0))
            winner = best.get("username")

        result = {
            "profiles": profiles,
            "winner": winner,
            "insights": comparison_insights,
        }

        await set_job_status(job_id, "completed", 100, "Comparison complete", result=result)
        logger.info("Compare job %s: completed with %d profiles.", job_id, len(profiles))

    except Exception as exc:
        logger.error("Compare job %s failed: %s", job_id, exc, exc_info=True)
        await set_job_status(
            job_id, "failed", 0, "Comparison failed", error=str(exc)
        )


@router.post("/compare", response_model=JobResponse)
@limiter.limit("20/minute")
async def submit_comparison(
    request: Request,
    body: CompareRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """
    Submit a multi-profile comparison job.

    Accepts 2-5 profile URLs and returns a job_id to poll for comparison results.
    """
    job_id = create_job_id()
    await set_job_status(
        job_id,
        "submitted",
        0,
        f"Comparison job queued for {len(body.urls)} profiles.",
    )

    background_tasks.add_task(_run_comparison, job_id, body.urls)
    logger.info("Compare job %s submitted for %d URLs.", job_id, len(body.urls))

    return JobResponse(
        job_id=job_id,
        status="submitted",
        message=f"Comparison of {len(body.urls)} profiles submitted. Poll /compare/{{job_id}} for results.",
    )


@router.get("/compare/{job_id}", response_model=JobStatusResponse)
async def get_comparison_status(job_id: str) -> JobStatusResponse:
    """Poll the status of a comparison job."""
    job = await get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Comparison job '{job_id}' not found or expired.",
        )

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        message=job.get("message", ""),
        result=job.get("result"),
        error=job.get("error"),
    )
