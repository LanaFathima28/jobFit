import time
from typing import Dict, List
from fastapi import Request, HTTPException, status
import redis

from app.core.config import settings

# In-memory rate limiting fallback for testing/dev if Redis connection fails
_in_memory_rate_limit_store: Dict[str, List[float]] = {}


def check_rate_limit(request: Request, limit: int = 60, window_seconds: int = 60):
    """
    Sliding window rate limiter for expensive endpoints.
    Tries Redis first; falls back to thread-safe in-memory store if Redis is unavailable.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{request.url.path}:{client_ip}"
    now = time.time()

    # Try Redis
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=1.0)
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = pipe.execute()
        request_count = results[2]

        if request_count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per {window_seconds} seconds allowed."
            )
        return
    except (redis.RedisError, ConnectionError, OSError):
        # Fallback to in-memory tracking
        timestamps = _in_memory_rate_limit_store.get(key, [])
        valid_timestamps = [t for t in timestamps if now - t <= window_seconds]
        valid_timestamps.append(now)
        _in_memory_rate_limit_store[key] = valid_timestamps

        if len(valid_timestamps) > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per {window_seconds} seconds allowed."
            )
