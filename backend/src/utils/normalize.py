"""领域规范化函数：手机 / 邮箱 / 姓名 / 地址 / 城市。

规范化口径写死在代码里并作为 MergeRule.normalization 默认值持久化，
保证同一份原始值在不同运行中得到相同 blocking 键与相似度。
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

_PHONE_STRIP = re.compile(r"[^\d]")
_ADDRESS_PUNCT = re.compile(r"[\s,，.。;；:：、/\\\-—()（）#号栋室楼层单元座幢|]+")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[a-z0-9]+")


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", value).strip()
    return text or None


def normalize_phone(value: str | None) -> str | None:
    """去分隔符/国家码，保留最后 11 位中国大陆手机号。"""
    if not value:
        return None
    digits = _PHONE_STRIP.sub("", unicodedata.normalize("NFKC", value))
    if not digits:
        return None
    if digits.startswith("0086"):
        digits = digits[4:]
    elif digits.startswith("86") and len(digits) > 11:
        digits = digits[2:]
    if len(digits) > 11:
        digits = digits[-11:]
    return digits or None


def phone_suffix(value: str | None, size: int = 4) -> str | None:
    normalized = normalize_phone(value)
    if not normalized or len(normalized) < size:
        return None
    return normalized[-size:]


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    text = unicodedata.normalize("NFKC", value).strip().lower()
    if "@" not in text or text.startswith("@") or text.endswith("@"):
        return None
    return text


def email_domain(value: str | None) -> str | None:
    normalized = normalize_email(value)
    if not normalized:
        return None
    return normalized.split("@", 1)[1]


def normalize_name(value: str | None) -> str | None:
    """去空白与标点、全角转半角、英文小写。"""
    if not value:
        return None
    text = unicodedata.normalize("NFKC", value)
    text = re.sub(r"[\s·•.。,，、()（）\-_]+", "", text)
    return text.lower() or None


def name_initial(value: str | None) -> str | None:
    """姓氏首字（中文取首字，英文取首字母）。"""
    normalized = normalize_name(value)
    if not normalized:
        return None
    return normalized[0]


def normalize_city(value: str | None) -> str | None:
    if not value:
        return None
    text = unicodedata.normalize("NFKC", value).strip()
    text = re.sub(r"(特别行政区|自治州|地区|市|县|区)$", "", text)
    return text or None


def normalize_address(value: str | None) -> str | None:
    """去标点/编号单位后缀，保留可比较的中文与门牌主干。"""
    if not value:
        return None
    text = unicodedata.normalize("NFKC", value).strip().lower()
    text = _ADDRESS_PUNCT.sub("", text)
    return text or None


def address_tokens(value: str | None) -> list[str]:
    """地址分词：拉丁/数字按词切，中文按 2-gram 切（Token Jaccard 输入）。"""
    normalized = normalize_address(value)
    if not normalized:
        return []
    tokens: list[str] = []
    tokens.extend(_LATIN.findall(normalized))
    cjk_chars = _CJK.findall(normalized)
    if len(cjk_chars) == 1:
        tokens.append(cjk_chars[0])
    else:
        tokens.extend("".join(cjk_chars[i : i + 2]) for i in range(len(cjk_chars) - 1))
    # 去重保序
    seen: set[str] = set()
    unique = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


DEFAULT_NORMALIZATION: dict[str, Any] = {
    "phone": "strip_non_digit+drop_country_code+last11",
    "email": "lowercase+trim",
    "name": "nfkc+strip_space_punct+lower",
    "city": "strip_city_suffix",
    "address": "nfkc+strip_punct+bigram_tokens",
    "blocking_keys": ["phone_suffix", "name_city", "email_domain"],
}


def build_blocking_keys(
    name: str | None, city: str | None, phone: str | None, email: str | None
) -> dict[str, str | None]:
    initial = name_initial(name)
    city_key = normalize_city(city)
    return {
        "phone_suffix": phone_suffix(phone),
        "name_city": f"{initial}|{city_key}" if initial and city_key else None,
        "email_domain": email_domain(email),
    }
