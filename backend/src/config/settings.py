"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "entresolv"
    db_user: str = "entresolv"
    db_password: str = "entresolv_pw_2026"

    # 安全
    jwt_secret: str = "entresolv-jwt-secret-change-me-2026"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    refresh_token_days: int = 7

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    evidence_dir: str = "/data/evidence"
    seed_demo: bool = True

    # 算法默认参数（MergeRule 落库后可覆盖）
    auto_threshold: float = 0.92
    review_threshold: float = 0.75

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
