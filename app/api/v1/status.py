"""API route: GET /status/{job_id} — generic job status check."""
from fastapi import APIRouter, HTTPException
from app.schemas.common import JobStatusResponse
from app.services.cache_service import get_job_status

router = APIRouter()


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str) -> JobStatusResponse:
    """
    Generic job status check — works for any analysis, profile, or comparison job.

    Args:
        job_id: The job identifier.

    Returns:
        Current job status, progress, and result (if completed).
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
