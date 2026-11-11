"""共享枚举 1/2：来源系统、判定、状态、角色相关领域枚举。

前后端各一份：backend 见本文件，frontend 见 src/constants/resolution.ts。
"""
from __future__ import annotations

from enum import Enum


class SourceSystem(str, Enum):
    POS = "pos"
    ECOMMERCE = "ecommerce"
    SERVICE = "service"


SOURCE_SYSTEM_LABELS: dict[str, str] = {
    SourceSystem.POS.value: "POS 收银",
    SourceSystem.ECOMMERCE.value: "电商商城",
    SourceSystem.SERVICE.value: "客服工单",
}


class CandidateDecision(str, Enum):
    AUTO = "auto"
    REVIEW = "review"
    REJECT = "reject"


class CandidateStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ClusterStatus(str, Enum):
    AUTO_MERGED = "auto_merged"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    # 人工重新成组后被取代的原簇（成员集合已不再是当前分组）
    SPLIT = "split"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GoldenStatus(str, Enum):
    ACTIVE = "active"
    PROVISIONAL = "provisional"
    # 所属簇被拆分后退役的档案：不再下发营销，仅留档可查
    RETIRED = "retired"


class BlockingKey(str, Enum):
    PHONE_SUFFIX = "phone_suffix"
    NAME_CITY = "name_city"
    EMAIL_DOMAIN = "email_domain"


BLOCKING_KEY_LABELS: dict[str, str] = {
    BlockingKey.PHONE_SUFFIX.value: "手机后 4 位",
    BlockingKey.NAME_CITY.value: "姓名首字 + 城市",
    BlockingKey.EMAIL_DOMAIN.value: "邮箱域名",
}

FIELD_LABELS: dict[str, str] = {
    "name": "姓名",
    "phone": "手机",
    "email": "邮箱",
    "address": "地址",
}
