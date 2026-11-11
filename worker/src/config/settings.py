"""worker 侧配置（与 backend 共享环境变量）。"""
from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus


class WorkerSettings:
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{os.environ.get('DB_USER', 'entresolv')}:"
            f"{quote_plus(os.environ.get('DB_PASSWORD', 'entresolv_pw_2026'))}@"
            f"{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/"
            f"{os.environ.get('DB_NAME', 'entresolv')}"
        )

    @property
    def redis_url(self) -> str:
        return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()


settings = get_settings()
