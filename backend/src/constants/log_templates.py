"""日志模板常量：避免字符串散落。"""
from __future__ import annotations

LOG_TEMPLATES = {
    "run_started": "run=%s status=running records=%s",
    "run_finished": "run=%s status=succeeded candidates=%s clusters=%s duration_ms=%s",
    "run_failed": "run=%s status=failed error=%s",
    "candidate_reviewed": "candidate=%s action=%s actor=%s",
    "rule_updated": "rule=%s version=%s actor=%s",
    "seed_summary": "SEED_SUMMARY %s",
}
