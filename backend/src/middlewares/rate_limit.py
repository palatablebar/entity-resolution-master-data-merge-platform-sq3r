"""Redis 滑动窗口限流（user + bucket 维度）。"""
from __future__ import annotations

import time

from fastapi import Depends, Request

from src.constants import error_codes as codes
from src.constants.limits import RATE_LIMIT_DEFAULT_PER_MINUTE, RATE_LIMIT_RUNS_PER_MINUTE
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.utils.errors import AppError
from src.utils.redis_client import get_redis


def _check(key: str, limit: int, window_seconds: int = 60) -> None:
    now = time.time()
    client = get_redis()
    pipeline = client.pipeline()
    pipeline.zremrangebyscore(key, 0, now - window_seconds)
    pipeline.zadd(key, {f"{now}:{time.perf_counter_ns()}": now})
    pipeline.zcard(key)
    pipeline.expire(key, window_seconds)
    results = pipeline.execute()
    count = int(results[2])
    if count > limit:
        raise AppError(
            codes.RATE_LIMITED,
            "请求过于频繁，请稍后重试",
            f"key={key} count={count} limit={limit}",
            extra={"retry_after": window_seconds},
        )


def rate_limit(bucket: str = "default"):
    limit = RATE_LIMIT_RUNS_PER_MINUTE if bucket == "runs" else RATE_LIMIT_DEFAULT_PER_MINUTE

    def dependency(request: Request, user: User = Depends(get_current_user)) -> None:
        _check(f"ratelimit:{bucket}:{user.id}:{request.url.path}", limit)

    return Depends(dependency)
