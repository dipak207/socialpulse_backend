"""Redis-backed caching service for SocialPulse Intelligence."""

import json
import hashlib
import os

from datetime import datetime
from typing import Any, Optional

import redis.asyncio as aioredis

from app.utils.logger import logger

# --------------------------------------------------
# REDIS
# --------------------------------------------------

_redis_client: Optional[aioredis.Redis] = None

REDIS_URL: str = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379"
)

REDIS_TTL_SECONDS: int = int(
    os.getenv("REDIS_TTL_SECONDS", "3600")
)

JOB_TTL_SECONDS: int = 3600

# --------------------------------------------------
# MEMORY FALLBACK
# --------------------------------------------------

_MEMORY_CACHE: dict[str, Any] = {}

# --------------------------------------------------
# REDIS INIT
# --------------------------------------------------

async def init_redis() -> None:
    global _redis_client

    try:
        client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        await client.ping()

        _redis_client = client

        logger.info(
            "Redis connected successfully: %s",
            REDIS_URL
        )

    except Exception as exc:
        _redis_client = None

        logger.warning(
            "Redis unavailable (%s). Using in-memory cache.",
            exc
        )

# --------------------------------------------------
# CLOSE
# --------------------------------------------------

async def close_redis() -> None:
    global _redis_client

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None

# --------------------------------------------------
# CACHE KEY
# --------------------------------------------------

def make_cache_key(prefix: str, *args: Any) -> str:
    raw = ":".join(str(a) for a in args)

    hashed = hashlib.md5(
        raw.encode("utf-8")
    ).hexdigest()

    return f"sp:{prefix}:{hashed}"

# --------------------------------------------------
# GET CACHE
# --------------------------------------------------

async def get_cached(key: str) -> Optional[Any]:

    # Redis path
    if _redis_client:
        try:
            raw = await _redis_client.get(key)

            if raw is None:
                return None

            return json.loads(raw)

        except Exception as exc:
            logger.warning(
                "Redis GET failed for key=%s: %s",
                key,
                exc
            )

    # Memory fallback
    return _MEMORY_CACHE.get(key)

# --------------------------------------------------
# SET CACHE
# --------------------------------------------------

async def set_cached(
    key: str,
    value: Any,
    ttl_seconds: int = REDIS_TTL_SECONDS
) -> None:

    serialized = json.dumps(
        value,
        default=str
    )

    # Redis path
    if _redis_client:
        try:
            await _redis_client.setex(
                key,
                ttl_seconds,
                serialized
            )
            return

        except Exception as exc:
            logger.warning(
                "Redis SET failed for key=%s: %s",
                key,
                exc
            )

    # Memory fallback
    _MEMORY_CACHE[key] = value

# --------------------------------------------------
# JOB STATUS
# --------------------------------------------------

async def set_job_status(
    job_id: str,
    status: str,
    progress: int,
    message: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:

    payload: dict = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": datetime.utcnow().isoformat(),
    }

    if result is not None:
        payload["result"] = result

    if error is not None:
        payload["error"] = error

    key = f"sp:job:{job_id}"

    await set_cached(
        key,
        payload,
        ttl_seconds=JOB_TTL_SECONDS
    )

# --------------------------------------------------
# GET JOB STATUS
# --------------------------------------------------

async def get_job_status(
    job_id: str
) -> Optional[dict]:

    key = f"sp:job:{job_id}"

    return await get_cached(key)

# --------------------------------------------------
# DELETE
# --------------------------------------------------

async def delete_cached(key: str) -> None:

    if _redis_client:
        try:
            await _redis_client.delete(key)

        except Exception as exc:
            logger.warning(
                "Redis DELETE failed for key=%s: %s",
                key,
                exc
            )

    _MEMORY_CACHE.pop(key, None)

# --------------------------------------------------
# EXPORTS
# --------------------------------------------------

__all__ = [
    "init_redis",
    "close_redis",
    "make_cache_key",
    "get_cached",
    "set_cached",
    "set_job_status",
    "get_job_status",
    "delete_cached",
]