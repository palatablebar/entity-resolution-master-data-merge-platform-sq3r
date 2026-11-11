"""相似度原语：Jaro-Winkler（自实现）、Token Jaccard、归一化精确匹配。"""
from __future__ import annotations


def jaro(a: str, b: str) -> float:
    """经典 Jaro 相似度。空串与自身相等均按定义处理。"""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    len_a, len_b = len(a), len(b)
    match_distance = max(len_a, len_b) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    a_matches = [False] * len_a
    b_matches = [False] * len_b
    matches = 0
    for i in range(len_a):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len_b)
        for j in range(start, end):
            if b_matches[j] or a[i] != b[j]:
                continue
            a_matches[i] = True
            b_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0

    transpositions = 0
    k = 0
    for i in range(len_a):
        if not a_matches[i]:
            continue
        while not b_matches[k]:
            k += 1
        if a[i] != b[k]:
            transpositions += 1
        k += 1
    transpositions //= 2
    return (matches / len_a + matches / len_b + (matches - transpositions) / matches) / 3.0


def jaro_winkler(a: str, b: str, prefix_scale: float = 0.1, max_prefix: int = 4, boost_threshold: float = 0.7) -> float:
    """Jaro-Winkler：对公共前缀加权，仅当 Jaro 高于阈值时生效。"""
    jaro_score = jaro(a, b)
    if jaro_score <= boost_threshold:
        return jaro_score
    prefix = 0
    for left, right in zip(a, b):
        if left != right or prefix >= max_prefix:
            break
        prefix += 1
    return min(1.0, jaro_score + prefix * prefix_scale * (1.0 - jaro_score))


def token_jaccard(left: list[str], right: list[str]) -> float | None:
    """集合交并比。任一侧为空返回 None（视为该字段缺失，不参与加权）。"""
    if not left or not right:
        return None
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    if not union:
        return None
    return len(left_set & right_set) / len(union)


def normalized_exact(left: str | None, right: str | None) -> float | None:
    """归一化后精确匹配：两边都有值才算可用。"""
    if not left or not right:
        return None
    return 1.0 if left == right else 0.0
