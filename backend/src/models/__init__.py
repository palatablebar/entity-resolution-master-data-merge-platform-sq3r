"""模型汇总：脚本 / alembic 只需 import Base 即可完成注册。"""
from src.models.base import Base
from src.models.user import User
from src.models.audit_log import AuditLog
from src.models.source_record import SourceRecord
from src.models.merge_rule import MergeRule
from src.models.resolution_run import ResolutionRun
from src.models.match_candidate import MatchCandidate
from src.models.entity_cluster import EntityCluster
from src.models.golden_record import GoldenRecord

__all__ = [
    "Base",
    "User",
    "AuditLog",
    "SourceRecord",
    "MergeRule",
    "ResolutionRun",
    "MatchCandidate",
    "EntityCluster",
    "GoldenRecord",
]
