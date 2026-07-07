from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from app.db.file_storage import log_report
from app.services.shared.reporting_service import reporting_service
from app.core import storage_paths

router = APIRouter()

REPORTS_FILE = storage_paths.REPORTS_DIR / "reports.csv"


def _list_reports(
    report_types: Optional[list[str]] = None,
    user_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    decision: Optional[str] = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    return reporting_service.list_reports(
        report_types=report_types,
        user_id=user_id,
        transaction_id=transaction_id,
        decision=decision,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/reports")
def get_reports(
    user_id: Optional[str] = Query(default=None),
    transaction_id: Optional[str] = Query(default=None),
    decision: Optional[str] = Query(default=None),
    report_type: Optional[str] = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
):
    report_types = [report_type] if report_type else None
    return _list_reports(
        report_types=report_types,
        user_id=user_id,
        transaction_id=transaction_id,
        decision=decision,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/reports/sar")
def get_sar_reports(
    user_id: Optional[str] = Query(default=None),
    transaction_id: Optional[str] = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    return _list_reports(
        report_types=["SAR"],
        user_id=user_id,
        transaction_id=transaction_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/str")
def get_str_reports(
    user_id: Optional[str] = Query(default=None),
    transaction_id: Optional[str] = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    return _list_reports(
        report_types=["STR"],
        user_id=user_id,
        transaction_id=transaction_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/high-risk")
def get_high_risk_reports(
    user_id: Optional[str] = Query(default=None),
    transaction_id: Optional[str] = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    return _list_reports(
        report_types=["HIGH_RISK_ONBOARDING", "MULE_ACCOUNT_ALERT"],
        user_id=user_id,
        transaction_id=transaction_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/manual-review")
def get_manual_review_reports(
    user_id: Optional[str] = Query(default=None),
    transaction_id: Optional[str] = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    return _list_reports(
        report_types=["MANUAL_REVIEW_ESCALATION"],
        user_id=user_id,
        transaction_id=transaction_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.post("/reports")
def create_report(payload: dict):
    record = {
        "report_type": payload.get("report_type", "MANUAL_REVIEW_ESCALATION"),
        "user_id": payload.get("user_id", ""),
        "transaction_id": payload.get("transaction_id", ""),
        "decision": payload.get("decision", ""),
        "final_score": payload.get("final_score", 0),
        "behavior_score": payload.get("behavior_score", 0),
        "sequence_score": payload.get("sequence_score", 0),
        "graph_score": payload.get("graph_score", 0),
        "rule_score": payload.get("rule_score", 0),
        "officer_recommendation": payload.get("officer_recommendation", ""),
        "immediate_action": payload.get("immediate_action", ""),
        "reason": payload.get("reason", ""),
        "reasons": payload.get("reasons", []),
        "amount": payload.get("amount", 0),
        "source_engine": payload.get("source_engine", "REPORT_API"),
        "escalation_level": payload.get("escalation_level", payload.get("report_type", "MANUAL_REVIEW_ESCALATION")),
        "review_status": payload.get("review_status", "AUTO"),
        "evidence": payload.get("evidence", []),
        "metadata": payload.get("metadata", {}),
    }
    log_report(record)
    return record


@router.get("/reports/export")
def export_reports(format: str = Query(default="json")):
    if not REPORTS_FILE.exists():
        if format.lower() == "csv":
            return ""
        return json.dumps([], ensure_ascii=False)

    import pandas as pd

    df = pd.read_csv(REPORTS_FILE)
    fmt = format.lower()
    if fmt == "csv":
        return df.to_csv(index=False)
    if fmt == "pdf":
        return json.dumps({"format": "pdf", "rows": df.to_dict(orient="records")}, ensure_ascii=False)
    return df.to_json(orient="records")