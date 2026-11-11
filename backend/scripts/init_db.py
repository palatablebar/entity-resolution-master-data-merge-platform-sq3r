"""建表 + 等待数据库就绪。entrypoint 在 uvicorn 之前调用；可重复执行。"""
from __future__ import annotations

import sys
import time

from sqlalchemy import text

from src.config.database import engine
from src.config.settings import settings
from src.models import Base  # noqa: F401 - 触发全部模型注册


def wait_for_db(attempts: int = 30, delay: float = 2.0) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"database not ready: {last_error}")


def main() -> int:
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    print(f"[init_db] schema ready db={settings.db_name} tables={len(Base.metadata.tables)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
