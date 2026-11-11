"""算法默认权重与来源可靠性（MergeRule 落库时可覆盖）。

字段权重合计 1.0：姓名 0.40 / 手机 0.30 / 邮箱 0.10 / 地址 0.20。
来源可靠性：POS 0.90 / 电商 0.80 / 客服 0.60。
时间衰减半衰期 30 天：reliability = 源权重 × 字段完整度 × 0.5^(days/30)。
"""
from __future__ import annotations

DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "name": 0.40,
    "phone": 0.30,
    "email": 0.10,
    "address": 0.20,
}

DEFAULT_SOURCE_RELIABILITY: dict[str, float] = {
    "pos": 0.90,
    "ecommerce": 0.80,
    "service": 0.60,
}

TIME_DECAY_HALF_LIFE_DAYS = 30.0
