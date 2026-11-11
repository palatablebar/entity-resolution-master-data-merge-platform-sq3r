"""算法层输入视图：与 ORM 解耦，便于 worker / seed / 单测复用。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.utils.normalize import (
    address_tokens,
    build_blocking_keys,
    normalize_address,
    normalize_city,
    normalize_email,
    normalize_name,
    normalize_phone,
)


@dataclass
class RecordView:
    id: str
    source_system: str
    external_id: str
    full_name: str | None
    city: str | None
    phone: str | None
    email: str | None
    address: str | None
    source_updated_at: datetime | None
    normalized_name: str | None
    normalized_city: str | None
    normalized_phone: str | None
    normalized_email: str | None
    normalized_address: str | None

    @classmethod
    def from_model(cls, row: Any) -> "RecordView":
        return cls(
            id=str(row.id),
            source_system=row.source_system,
            external_id=row.external_id,
            full_name=row.full_name,
            city=row.city,
            phone=row.phone,
            email=row.email,
            address=row.address,
            source_updated_at=row.source_updated_at,
            normalized_name=row.normalized_name or normalize_name(row.full_name),
            normalized_city=row.normalized_city or normalize_city(row.city),
            normalized_phone=row.normalized_phone or normalize_phone(row.phone),
            normalized_email=row.normalized_email or normalize_email(row.email),
            normalized_address=row.normalized_address or normalize_address(row.address),
        )

    def blocking_keys(self) -> dict[str, str | None]:
        return build_blocking_keys(self.full_name, self.city, self.phone, self.email)

    def address_tokens(self) -> list[str]:
        return address_tokens(self.address)

    def display_key(self) -> str:
        return f"{self.source_system}:{self.external_id}"
