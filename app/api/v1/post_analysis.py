"""API routes: POST /post-analysis, GET /post-analysis/{job_id}."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from app.schemas.common import URLRequest, JobResponse, JobStatusResponse
from app.services.analysis_service import create_job_id, analyze_post_async
from app.services.cache_service import set_job_status, get_job_status
from app.utils.rate_limiter import limiter
from app.utils.logger import logger

router = APIRouter()


@router.post("/post-analysis", response_model=JobResponse)
@limiter.limit("30/minute")
async def submit_post_analysis(
    request: Request,
    body: URLRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """
    Submit a post analysis job.

    Creates a background task to fetch and analyze the given post URL.
    Returns immediately with a job_id to poll for results.
    """
    job_id = create_job_id()
    await set_job_status(job_id, "submitted", 0, "Job queued. Analysis will begin shortly.")

    background_tasks.add_task(analyze_post_async, job_id, body.url, body.timeframe or "30d")
    logger.info("Post analysis job %s submitted for URL: %s", job_id, body.url)

    return JobResponse(
        job_id=job_id,
        status="submitted",
        message="Analysis job submitted. Poll /post-analysis/{job_id} for results.",
    )


@router.get("/post-analysis/{job_id}", response_model=JobStatusResponse)
async def get_post_analysis_status(job_id: str) -> JobStatusResponse:
    """
    Poll the status of a post analysis job.

    Returns current progress and final result when completed.
    """
    job = await get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may have expired (TTL: 1 hour).",
        )

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        message=job.get("message", ""),
        result=job.get("result"),
        error=job.get("error"),
    )
