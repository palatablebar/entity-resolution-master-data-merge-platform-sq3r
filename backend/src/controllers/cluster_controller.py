"""簇 controller。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import cluster_service


def list_clusters(
    db: Session, *, run_id: str | None, status: str | None, page: int, page_size: int
) -> dict:
    return cluster_service.list_clusters(
        db, run_id=run_id, status=status, page=page, page_size=page_size
    )


def get_cluster(db: Session, cluster_id: str) -> dict:
    return cluster_service.get_cluster(db, cluster_id)
