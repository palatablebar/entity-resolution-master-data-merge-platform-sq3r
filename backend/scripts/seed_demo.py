"""幂等演示数据：`python -m scripts.seed_demo`。

模拟客户：区域连锁药房「康和」会员主数据治理组。上游三套系统（POS / 电商 / 客服）
导出 120 条会员记录，其中 18 组跨系统重复、4 组同名不同人。

自然键：
  - User.email
  - MergeRule.name
  - SourceRecord(source_system, external_id)
  - ResolutionRun.run_label
重复执行只输出 SEED_SKIPPED，不新增、不覆盖人工修改；结束时打印
`SEED_SUMMARY {json}`（各核心实体行数），供幂等校验。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config.database import session_scope
from src.constants.enums import ClusterStatus, GoldenStatus, RunStatus
from src.constants.roles import ROLE_ADMIN, ROLE_CURATOR, ROLE_MARKETING
from src.constants.weights import DEFAULT_FIELD_WEIGHTS, DEFAULT_SOURCE_RELIABILITY
from src.models.entity_cluster import EntityCluster
from src.models.golden_record import GoldenRecord
from src.models.match_candidate import MatchCandidate
from src.models.merge_rule import MergeRule
from src.models.resolution_run import ResolutionRun
from src.models.source_record import SourceRecord
from src.models.user import User
from src.services import resolution_service
from src.utils.normalize import (
    DEFAULT_NORMALIZATION,
    normalize_address,
    normalize_city,
    normalize_email,
    normalize_name,
    normalize_phone,
)
from src.utils.password import hash_password

DEMO_PASSWORD = "Demo@2026"
DEMO_USERS = [
    ("admin@master.local", "康和药房 · 主数据管理员", ROLE_ADMIN),
    ("curator@master.local", "康和药房 · 数据管家", ROLE_CURATOR),
    ("marketing@master.local", "康和药房 · 营销运营", ROLE_MARKETING),
]

RULE_BASE = "康和会员主数据 v1"
RULE_TIGHT = "康和会员主数据 v1 · 阈值收紧预演"
RUN_LABEL_BASELINE = "2026-11 月度解析基线"
RUN_LABEL_TIGHT = "阈值收紧预演 · auto 0.99 / review 0.88"

TZ = timezone.utc
BASE_REFERENCE = datetime(2026, 11, 9, 2, 30, tzinfo=TZ)
SOURCE_UPDATED_AT = {
    "pos": datetime(2026, 11, 8, 9, 0, tzinfo=TZ),
    "ecommerce": datetime(2026, 11, 5, 14, 0, tzinfo=TZ),
    "service": datetime(2026, 10, 28, 11, 0, tzinfo=TZ),
}
SOURCE_PREFIX = {"pos": "POS", "ecommerce": "EC", "service": "CS"}
SOURCE_CYCLE = ["pos", "ecommerce", "service"]

CITIES = ["成都", "绵阳", "德阳", "宜宾", "南充", "泸州"]
DISTRICTS = ["武侯区", "锦江区", "青羊区", "成华区", "涪城区", "旌阳区"]
STREETS = ["人民南路四段", "春熙路", "光华村街", "建设北路", "临园路东段", "长江西路"]
DOMAINS = ["163.com", "qq.com", "gmail.com", "outlook.com", "sina.com", "foxmail.com", "189.cn", "aliyun.com"]
SURNAMES = ["张", "王", "李", "赵", "陈", "刘", "杨", "黄", "周", "吴", "徐", "孙"]
GIVEN = ["伟", "芳", "娜", "敏", "静", "秀英", "丽", "强", "磊", "军", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀兰", "霞"]

CREATED = 0
SKIPPED = 0


def _log(kind: str, entity: str, key: str) -> None:
    global CREATED, SKIPPED
    if kind == "SEED_CREATED":
        CREATED += 1
    else:
        SKIPPED += 1
    print(f"{kind} entity={entity} key={key}", flush=True)


def created(entity: str, key: str) -> None:
    _log("SEED_CREATED", entity, key)


def skipped(entity: str, key: str) -> None:
    _log("SEED_SKIPPED", entity, key)


# ------------------------------------------------------------------ 数据构造 ----


def person_name(index: int) -> str:
    return SURNAMES[index % len(SURNAMES)] + GIVEN[(index // len(SURNAMES)) % len(GIVEN)]


def phone_for(index: int) -> str:
    return f"138{index:08d}"


def format_phone(raw: str) -> str:
    """电商导出常见格式：+86 138-0000-0001。"""
    digits = raw[3:]
    return f"+86 138-{digits[0:4]}-{digits[4:8]}"


def email_for(index: int) -> str:
    return f"member{index:03d}@{DOMAINS[index % len(DOMAINS)]}"


def full_address(city: str, district: str, street: str, number: int, unit: int, room: int) -> str:
    return f"{city}{district}{street}{number}号{unit}栋{room}室"


def spaced_address(city: str, district: str, street: str, number: int, unit: int, room: int) -> str:
    return f"{city} {district} {street}{number}号 {unit}栋 {room}室"


def short_address(city: str, district: str, street: str, number: int) -> str:
    return f"{city}{district}{street}{number}号"


def build_record(
    source_system: str,
    external_id: str,
    name: str,
    phone: str | None,
    email: str | None,
    address: str | None,
    city: str,
) -> dict[str, Any]:
    return {
        "source_system": source_system,
        "external_id": external_id,
        "full_name": name,
        "phone": phone,
        "email": email,
        "address": address,
        "city": city,
        "source_updated_at": SOURCE_UPDATED_AT[source_system],
        "raw_payload": {
            "name": name,
            "mobile": phone,
            "mail": email,
            "addr": address,
            "city": city,
            "exported_at": SOURCE_UPDATED_AT[source_system].isoformat(),
        },
    }


def build_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    counters = {key: 0 for key in SOURCE_PREFIX}

    def next_external(source_system: str) -> str:
        counters[source_system] += 1
        return f"{SOURCE_PREFIX[source_system]}-{counters[source_system]:04d}"

    # 18 组跨系统重复：前 12 组完全一致（自动合并），后 6 组地址已变（需复核）
    for group in range(18):
        name = person_name(group)
        city = CITIES[group % len(CITIES)]
        district = DISTRICTS[group % len(DISTRICTS)]
        street = STREETS[group % len(STREETS)]
        number = 100 + group * 7
        unit = (group % 6) + 1
        room = 1502 + group
        phone = phone_for(group)
        email = email_for(group)

        if group < 12:
            pos_address = full_address(city, district, street, number, unit, room)
            ecom_address = spaced_address(city, district, street, number, unit, room)
            service_address = short_address(city, district, street, number)
            ecom_phone = format_phone(phone)
        else:
            alt_district = DISTRICTS[(group + 3) % len(DISTRICTS)]
            alt_street = STREETS[(group + 2) % len(STREETS)]
            third_district = DISTRICTS[(group + 5) % len(DISTRICTS)]
            third_street = STREETS[(group + 4) % len(STREETS)]
            pos_address = full_address(city, district, street, number, unit, room)
            ecom_address = full_address(city, alt_district, alt_street, number + 88, unit + 1, room + 12)
            service_address = short_address(city, third_district, third_street, number + 501)
            ecom_phone = phone

        variants = [
            ("pos", pos_address, phone),
            ("ecommerce", ecom_address, ecom_phone),
            ("service", service_address, phone),
        ]
        for source_system, address, source_phone in variants:
            records.append(
                build_record(
                    source_system,
                    next_external(source_system),
                    name,
                    source_phone,
                    email,
                    address,
                    city,
                )
            )

    # 4 条同名不同人（陈立）：姓名相同、手机/邮箱/地址都不同 → 应被判 reject
    for index in range(4):
        source_system = SOURCE_CYCLE[index % len(SOURCE_CYCLE)]
        phone = f"139{index:08d}"
        email = f"chenli{index}@{DOMAINS[index]}"
        city = "成都"
        district = DISTRICTS[index % len(DISTRICTS)]
        street = STREETS[(index + 1) % len(STREETS)]
        address = full_address(city, district, street, 700 + index * 13, index + 1, 801 + index)
        records.append(
            build_record(source_system, next_external(source_system), "陈立", phone, email, address, city)
        )

    # 62 条单源唯一会员
    for index in range(62):
        person_index = 22 + index
        source_system = SOURCE_CYCLE[index % len(SOURCE_CYCLE)]
        city = CITIES[index % len(CITIES)]
        district = DISTRICTS[(index + 2) % len(DISTRICTS)]
        street = STREETS[(index + 4) % len(STREETS)]
        name = person_name(person_index)
        address = full_address(city, district, street, 300 + index * 3, (index % 5) + 1, 601 + index)
        records.append(
            build_record(
                source_system,
                next_external(source_system),
                name,
                phone_for(person_index),
                email_for(person_index),
                address,
                city,
            )
        )

    assert len(records) == 120, f"expect 120 demo records, got {len(records)}"
    return records


# ------------------------------------------------------------------ 幂等写入 ----


def seed_users(db: Session) -> None:
    for email, display_name, role in DEMO_USERS:
        existing = db.query(User).filter(User.email == email).first()
        if existing is not None:
            skipped("User", email)
            continue
        db.add(
            User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=display_name,
                role=role,
                is_active=True,
            )
        )
        created("User", email)
    db.commit()


def seed_rules(db: Session) -> dict[str, MergeRule]:
    specs = [
        (RULE_BASE, 0.92, 0.75, True),
        (RULE_TIGHT, 0.99, 0.88, False),
    ]
    result: dict[str, MergeRule] = {}
    for name, auto_threshold, review_threshold, is_active in specs:
        existing = db.query(MergeRule).filter(MergeRule.name == name).first()
        if existing is not None:
            skipped("MergeRule", name)
            result[name] = existing
            continue
        rule = MergeRule(
            name=name,
            field_weights=dict(DEFAULT_FIELD_WEIGHTS),
            source_reliability=dict(DEFAULT_SOURCE_RELIABILITY),
            auto_threshold=auto_threshold,
            review_threshold=review_threshold,
            normalization=dict(DEFAULT_NORMALIZATION),
            is_active=is_active,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        created("MergeRule", name)
        result[name] = rule
    return result


def seed_records(db: Session) -> None:
    for spec in build_records():
        existing = (
            db.query(SourceRecord)
            .filter(
                SourceRecord.source_system == spec["source_system"],
                SourceRecord.external_id == spec["external_id"],
            )
            .first()
        )
        if existing is not None:
            skipped("SourceRecord", f"{spec['source_system']}:{spec['external_id']}")
            continue
        db.add(
            SourceRecord(
                source_system=spec["source_system"],
                external_id=spec["external_id"],
                full_name=spec["full_name"],
                phone=spec["phone"],
                email=spec["email"],
                address=spec["address"],
                city=spec["city"],
                normalized_name=normalize_name(spec["full_name"]),
                normalized_phone=normalize_phone(spec["phone"]),
                normalized_email=normalize_email(spec["email"]),
                normalized_address=normalize_address(spec["address"]),
                normalized_city=normalize_city(spec["city"]),
                source_updated_at=spec["source_updated_at"],
                raw_payload=spec["raw_payload"],
            )
        )
        created("SourceRecord", f"{spec['source_system']}:{spec['external_id']}")
    db.commit()


def _seed_run(
    db: Session,
    *,
    label: str,
    rule: MergeRule,
    reference_time: datetime,
) -> ResolutionRun | None:
    existing = db.query(ResolutionRun).filter(ResolutionRun.run_label == label).first()
    if existing is not None:
        skipped("ResolutionRun", label)
        return None
    run = ResolutionRun(
        rule_id=rule.id,
        run_label=label,
        status=RunStatus.QUEUED.value,
        params_json={
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "rule_version": rule.version,
            "field_weights": dict(rule.field_weights),
            "source_reliability": dict(rule.source_reliability),
            "auto_threshold": rule.auto_threshold,
            "review_threshold": rule.review_threshold,
            "seed_reference_time": reference_time.isoformat(),
        },
        blocking_keys=["phone_suffix", "name_city", "email_domain"],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    resolution_service.execute_run(db, run, rule, reference_time=reference_time)
    created("ResolutionRun", label)
    return run


def seed_review_states(db: Session, baseline: ResolutionRun) -> None:
    """基线运行落定后的人工复核痕迹：确认 1 簇、拒绝 3 簇、留 2 簇待复核。"""
    if db.query(MatchCandidate).filter(
        MatchCandidate.run_id == baseline.id,
        MatchCandidate.status != "pending",
    ).first() is not None:
        skipped("CandidateReview", f"run={baseline.run_label}")
        return

    curator = db.query(User).filter(User.email == "curator@master.local").first()
    clusters = (
        db.query(EntityCluster)
        .filter(EntityCluster.run_id == baseline.id, EntityCluster.edge_type == "review")
        .order_by(EntityCluster.cluster_key.asc())
        .all()
    )
    if not clusters:
        skipped("CandidateReview", f"run={baseline.run_label}")
        return

    review_time = BASE_REFERENCE + timedelta(hours=3)
    confirm_cluster = clusters[0]
    reject_clusters = clusters[1:4]

    def cluster_candidates(cluster: EntityCluster) -> list[MatchCandidate]:
        member_ids = [str(member) for member in cluster.member_ids]
        return (
            db.query(MatchCandidate)
            .filter(
                MatchCandidate.run_id == baseline.id,
                MatchCandidate.left_record_id.in_(member_ids),
                MatchCandidate.right_record_id.in_(member_ids),
            )
            .all()
        )

    for candidate in cluster_candidates(confirm_cluster):
        candidate.status = "confirmed"
        candidate.reviewed_by = curator.id if curator else None
        candidate.reviewed_at = review_time
        candidate.review_note = "姓名/手机/邮箱一致，地址为搬家后新址，确认同一会员"
    confirm_cluster.status = ClusterStatus.CONFIRMED.value
    confirm_cluster.review_notes = {
        "confirmed_by": "curator@master.local",
        "confirmed_at": review_time.isoformat(),
        "note": "地址变更已核实",
    }
    confirm_golden = (
        db.query(GoldenRecord).filter(GoldenRecord.cluster_id == confirm_cluster.id).first()
    )
    if confirm_golden is not None:
        confirm_golden.status = GoldenStatus.ACTIVE.value

    for cluster in reject_clusters:
        for candidate in cluster_candidates(cluster):
            candidate.status = "rejected"
            candidate.reviewed_by = curator.id if curator else None
            candidate.reviewed_at = review_time
            candidate.review_note = "地址与门牌均不同，判定为同名不同人，拒绝合并"
    db.commit()
    created("CandidateReview", f"run={baseline.run_label}")


def table_counts(db: Session) -> dict[str, int]:
    return {
        "source_record": db.query(func.count(SourceRecord.id)).scalar() or 0,
        "match_candidate": db.query(func.count(MatchCandidate.id)).scalar() or 0,
        "entity_cluster": db.query(func.count(EntityCluster.id)).scalar() or 0,
        "golden_record": db.query(func.count(GoldenRecord.id)).scalar() or 0,
        "merge_rule": db.query(func.count(MergeRule.id)).scalar() or 0,
        "resolution_run": db.query(func.count(ResolutionRun.id)).scalar() or 0,
        "user": db.query(func.count(User.id)).scalar() or 0,
    }


def seed_all() -> dict[str, Any]:
    global CREATED, SKIPPED
    CREATED = 0
    SKIPPED = 0
    with session_scope() as db:
        seed_users(db)
        rules = seed_rules(db)
        seed_records(db)

        tight_run = _seed_run(
            db,
            label=RUN_LABEL_TIGHT,
            rule=rules[RULE_TIGHT],
            reference_time=BASE_REFERENCE,
        )
        baseline_run = _seed_run(
            db,
            label=RUN_LABEL_BASELINE,
            rule=rules[RULE_BASE],
            reference_time=BASE_REFERENCE,
        )
        if baseline_run is not None:
            seed_review_states(db, baseline_run)
        elif tight_run is not None:
            # 基线已存在但收紧预演是本次新建：无需额外人工痕迹
            pass

        summary = table_counts(db)

    print("SEED_SUMMARY " + json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    print(f"SEED_DONE created={CREATED} skipped={SKIPPED}", flush=True)
    return {"created": CREATED, "skipped": SKIPPED, "summary": summary}


def main() -> int:
    try:
        result = seed_all()
    except Exception as exc:  # noqa: BLE001
        print(f"SEED_FAILED {exc}", file=sys.stderr, flush=True)
        raise
    print(f"SEED_RESULT {json.dumps(result['summary'], ensure_ascii=False, sort_keys=True)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
