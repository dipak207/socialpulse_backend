"""API route: POST /detect-platform — identify platform and content type from URL."""
from fastapi import APIRouter, Request
from app.schemas.common import URLRequest, DetectResponse
from app.utils.url_detector import URLDetector
from app.utils.rate_limiter import limiter
from app.utils.logger import logger

router = APIRouter()
_detector = URLDetector()


@router.post("/detect-platform", response_model=DetectResponse)
@limiter.limit("60/minute")
async def detect_platform(request: Request, body: URLRequest) -> DetectResponse:
    """
    Detect the social media platform and content type from a URL.

    Returns platform, content type, identifier, and display URL.
    Raises HTTP 422 for unsupported URLs.
    """
    logger.info("Detecting platform for URL: %s", body.url)
    result = _detector.detect(body.url)
    return DetectResponse(
        platform=result["platform"],
        type=result["type"],
        identifier=result["identifier"],
        display_url=result["display_url"],
    )
