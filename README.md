# SocialPulse Intelligence - Backend API

Public cross-platform social media intelligence API using FastAPI.

## Tech Stack
- FastAPI + Uvicorn
- PostgreSQL (asyncpg) + SQLAlchemy + Alembic
- Redis (Upstash) + APScheduler
- Playwright, instaloader, yt-dlp, google-api-python-client

## Setup
1. Copy `.env.example` to `.env`
2. `docker-compose up -d`
3. `alembic upgrade head`

## Endpoints
- `POST /api/v1/detect-platform`
- `POST /api/v1/post-analysis`
- `POST /api/v1/profile-analysis`
- `POST /api/v1/compare`
- `GET /api/v1/trending`
- `GET /api/v1/export/{job_id}`
- `GET /api/v1/status/{job_id}`
