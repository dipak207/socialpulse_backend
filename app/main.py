"""SocialPulse Intelligence — FastAPI application entry point."""

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import detect, post_analysis, profile, compare, trending, export, status
from app.workers.scheduler import start_scheduler, stop_scheduler
from app.services.cache_service import init_redis, close_redis
from app.utils.rate_limiter import limiter
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle manager."""
    logger.info("=" * 60)
    logger.info("Starting SocialPulse Intelligence API v1.0.0")
    logger.info("=" * 60)

    # Initialize Redis
    await init_redis()

    # Start background scheduler
    start_scheduler()

    logger.info("SocialPulse Intelligence API is ready.")
    yield

    # Shutdown
    logger.info("Shutting down SocialPulse Intelligence API...")
    stop_scheduler()
    await close_redis()
    logger.info("Shutdown complete.")


# Create FastAPI application
app = FastAPI(
    title="SocialPulse Intelligence API",
    description=(
        "Analyze any public social media URL across YouTube, Instagram, "
        "Twitter/X, TikTok, and LinkedIn. Get engagement metrics, virality scores, "
        "AI-generated insights, and exportable reports."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(detect.router, prefix="/api/v1", tags=["Detection"])
app.include_router(post_analysis.router, prefix="/api/v1", tags=["Post Analysis"])
app.include_router(profile.router, prefix="/api/v1", tags=["Profile Analysis"])
app.include_router(compare.router, prefix="/api/v1", tags=["Compare"])
app.include_router(trending.router, prefix="/api/v1", tags=["Trending"])
app.include_router(export.router, prefix="/api/v1", tags=["Export"])
app.include_router(status.router, prefix="/api/v1", tags=["Status"])


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "SocialPulse Intelligence",
        "version": "1.0.0",
    }


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint with API info."""
    return {
        "service": "SocialPulse Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "detect": "POST /api/v1/detect-platform",
            "post_analysis": "POST /api/v1/post-analysis",
            "profile_analysis": "POST /api/v1/profile-analysis",
            "compare": "POST /api/v1/compare",
            "trending": "GET /api/v1/trending",
            "export": "GET /api/v1/export/{job_id}",
            "status": "GET /api/v1/status/{job_id}",
        },
    }
