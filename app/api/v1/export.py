"""API route: GET /export/{job_id} — download analysis result as JSON, CSV, or PDF."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.cache_service import get_job_status
from app.services.report_service import report_service
from app.utils.logger import logger

router = APIRouter()

_CONTENT_TYPES = {
    "json": "application/json",
    "csv": "text/csv",
    "pdf": "application/pdf",
}

_EXTENSIONS = {
    "json": "json",
    "csv": "csv",
    "pdf": "pdf",
}


@router.get("/export/{job_id}")
async def export_analysis(
    job_id: str,
    format: str = Query("json", regex="^(json|csv|pdf)$", description="Export format"),
) -> Response:
    """
    Download the result of a completed analysis job.

    Args:
        job_id: The job identifier returned when submitting an analysis.
        format: Export format — 'json', 'csv', or 'pdf'.

    Returns:
        File download response with appropriate Content-Type header.

    Raises:
        404: If job not found or not yet completed.
        422: If the job failed or result is empty.
    """
    job = await get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found or expired (TTL: 1 hour).",
        )

    if job.get("status") != "completed":
        status = job.get("status", "unknown")
        progress = job.get("progress", 0)
        raise HTTPException(
            status_code=422,
            detail=f"Job is not completed yet. Status: {status}, Progress: {progress}%.",
        )

    result = job.get("result")
    if not result:
        raise HTTPException(
            status_code=422,
            detail="Job completed but result is empty. Cannot export.",
        )

    fmt = format.lower()
    logger.info("Exporting job %s as %s", job_id, fmt)

    try:
        if fmt == "json":
            content = report_service.to_json(result)
        elif fmt == "csv":
            content = report_service.to_csv(result)
        elif fmt == "pdf":
            content = report_service.to_pdf(result)
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported format: {fmt}")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Export failed for job %s: %s", job_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Export generation failed: {exc}",
        )

    platform = result.get("platform", "social")
    filename = f"socialpulse_{platform}_{job_id[:8]}.{_EXTENSIONS[fmt]}"

    return Response(
        content=content,
        media_type=_CONTENT_TYPES[fmt],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
