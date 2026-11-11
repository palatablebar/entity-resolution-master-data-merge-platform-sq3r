"""算法 1a：三路 blocking 键取并集 + 粗筛剪枝。

输入：RecordView 列表（已规范化）。
输出：被三路键命中的记录对（规范化 left<right）与原始命中对数。

键口径：
  - phone_suffix：手机归一化后后 4 位
  - name_city：姓名首字 + 去「市/区」后缀的城市
  - email_domain：邮箱归一化后的域名

剪枝：三路并集会产生大量弱对（尤其邮箱域名），因此保留满足下列任一条件的对，
其余计入 pruned_pairs（运行报告里如实展示）：
  - 手机后 4 位相同
  - 邮箱归一化相同
  - 姓名 Jaro-Winkler >= 0.82
"""
from __future__ import annotations

from dataclasses import dataclass

from src.algorithms.types import RecordView
from src.constants.limits import PRUNE_NAME_JW_MIN
from src.constants.enums import BlockingKey
from src.utils.normalize import phone_suffix
from src.utils.similarity import jaro_winkler

BLOCKING_KEY_ORDER: tuple[str, ...] = (
    BlockingKey.PHONE_SUFFIX.value,
    BlockingKey.NAME_CITY.value,
    BlockingKey.EMAIL_DOMAIN.value,
)


@dataclass(frozen=True)
class BlockedPair:
    left_id: str
    right_id: str
    keys: tuple[str, ...]


def build_index(records: list[RecordView]) -> dict[str, dict[str, list[int]]]:
    """key -> 键值 -> 记录下标列表。"""
    index: dict[str, dict[str, list[int]]] = {key: {} for key in BLOCKING_KEY_ORDER}
    for position, record in enumerate(records):
        for key, value in record.blocking_keys().items():
            if not value:
                continue
            index[key].setdefault(value, []).append(position)
    return index


def generate_blocked_pairs(records: list[RecordView]) -> tuple[list[BlockedPair], int]:
    """返回 (去重后的命中对, 原始命中对数)。"""
    index = build_index(records)
    hits: dict[tuple[int, int], list[str]] = {}
    for key in BLOCKING_KEY_ORDER:
        for positions in index[key].values():
            if len(positions) < 2:
                continue
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    first, second = positions[i], positions[j]
                    pair = (first, second) if first < second else (second, first)
                    bucket = hits.setdefault(pair, [])
                    if key not in bucket:
                        bucket.append(key)

    pairs = [
        BlockedPair(
            left_id=records[first].id,
            right_id=records[second].id,
            keys=tuple(keys),
        )
        for (first, second), keys in hits.items()
    ]
    pairs.sort(key=lambda pair: (pair.left_id, pair.right_id))
    return pairs, len(hits)


def prune_reason(left: RecordView, right: RecordView) -> str | None:
    """返回保留理由；None 表示应被剪掉。"""
    left_suffix = phone_suffix(left.phone)
    right_suffix = phone_suffix(right.phone)
    if left_suffix and left_suffix == right_suffix:
        return "phone_suffix"
    if left.normalized_email and left.normalized_email == right.normalized_email:
        return "email_exact"
    if left.normalized_name and right.normalized_name:
        if jaro_winkler(left.normalized_name, right.normalized_name) >= PRUNE_NAME_JW_MIN:
            return "name_similar"
    return None


def prune_pairs(
    pairs: list[BlockedPair], records: list[RecordView], index_by_id: dict[str, RecordView]
) -> tuple[list[BlockedPair], int]:
    kept: list[BlockedPair] = []
    pruned = 0
    for pair in pairs:
        left = index_by_id[pair.left_id]
        right = index_by_id[pair.right_id]
        if prune_reason(left, right) is None:
            pruned += 1
            continue
        kept.append(pair)
    return kept, pruned
