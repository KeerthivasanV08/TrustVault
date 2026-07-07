from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pandas as pd

from app.db.file_storage import log_explainability, log_report
from app.core import storage_paths

logger = logging.getLogger(__name__)

REPORTS_PATH = storage_paths.REPORTS_DIR / "reports.csv"

TRANSACTION_REPORT_TYPES = {
    "SAR",
    "STR",
    "MULE_ACCOUNT_ALERT",
    "MANUAL_REVIEW_ESCALATION",
}

ONBOARDING_REPORT_TYPES = {
    "HIGH_RISK_ONBOARDING",
    "MANUAL_REVIEW_ESCALATION",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def _as_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


class ReportingService:
    def __init__(self) -> None:
        self.reports_path = REPORTS_PATH

    def _load_reports_frame(self) -> pd.DataFrame:
        if self.reports_path.exists():
            try:
                return pd.read_csv(self.reports_path)
            except Exception:
                logger.exception("Failed to read reports.csv")
                return pd.DataFrame()
        return pd.DataFrame()

    def _write_report(self, record: Dict[str, Any]) -> Dict[str, Any]:
        report_id = record.get("report_id", str(uuid.uuid4()))
        record = {
            **record,
            "report_id": report_id,
            "timestamp": record.get("timestamp", _now()),
            "evidence": _to_json(record.get("evidence", [])),
            "reasons": _to_json(record.get("reasons", [])),
            "metadata": _to_json(record.get("metadata", {})),
        }
        log_report(record)
        for item in record.get("evidence_items", []):
            try:
                log_explainability({
                    "report_id": report_id,
                    "gate": item.get("gate", record.get("source_engine", "REPORTING")),
                    "user_id": record.get("user_id", ""),
                    "transaction_id": record.get("transaction_id", ""),
                    "category": item.get("category", "REPORT"),
                    "finding": item.get("finding", ""),
                    "evidence": item,
                    "metadata": record.get("metadata", {}),
                })
            except Exception:
                logger.exception("Failed to persist explainability evidence")
        return {k: v for k, v in record.items() if k != "evidence_items"}

    def _collect_reasons(self, *sources: Any) -> List[str]:
        reasons: List[str] = []
        for source in sources:
            for reason in _as_list(source):
                if reason and reason not in reasons:
                    reasons.append(reason)
        return reasons

    def _contains_any_substring(self, reasons: Sequence[str], needles: Sequence[str]) -> bool:
        for reason in reasons:
            upper_reason = str(reason).upper()
            if any(needle.upper() in upper_reason for needle in needles):
                return True
        return False

    def _build_transaction_evidence(self, decision_result: Mapping[str, Any], ml_result: Mapping[str, Any], sequence_result: Mapping[str, Any], graph_result: Mapping[str, Any], control_result: Mapping[str, Any]) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []

        for reason in _as_list(control_result.get("reason") or control_result.get("reasons")):
            evidence.append({"category": "REGULATORY", "finding": reason})

        for reason in _as_list(ml_result.get("reasons")):
            evidence.append({"category": "BEHAVIOR", "finding": reason})

        sequence_pattern = sequence_result.get("sequence_pattern")
        if sequence_pattern and sequence_pattern not in {"NONE", "INSUFFICIENT_HISTORY", "ERROR"}:
            evidence.append({"category": "SEQUENCE", "finding": sequence_pattern})

        for reason in _as_list(graph_result.get("reasons")):
            evidence.append({"category": "NETWORK", "finding": reason})

        if graph_result.get("known_fraud_neighbors", 0) > 0:
            evidence.append({"category": "NETWORK", "finding": "Connected to mule cluster"})

        if decision_result.get("decision") == "REVIEW":
            evidence.append({"category": "OFFICER", "finding": "Manual review required"})

        return evidence

    def _transaction_report_types(self, decision_result: Mapping[str, Any], control_result: Mapping[str, Any], sequence_result: Mapping[str, Any], graph_result: Mapping[str, Any], ml_result: Mapping[str, Any]) -> List[str]:
        report_types: List[str] = []

        decision = str(decision_result.get("decision", "")).upper()
        immediate_action = str(decision_result.get("immediate_action", "")).upper()
        control_status = str(control_result.get("status") or control_result.get("decision") or "").upper()

        structured_patterns = {"GATHER_SCATTER", "LAUNDERING_FLOW", "STRUCTURED_FRAGMENTATION", "SLOW_BLEED_PATTERN"}
        graph_mule_flag = graph_result.get("cluster_risk") == "HIGH" or graph_result.get("known_fraud_neighbors", 0) > 0
        trigger_reasons = self._collect_reasons(control_result.get("reason"), control_result.get("reasons"), ml_result.get("reasons"), sequence_result.get("sequence_pattern"))

        if control_status == "BLOCK" or decision == "BLOCK" or immediate_action in {"TRANSACTION_BLOCKED", "TRANSACTION_HALTED", "TRANSACTION_HALTED_ACCOUNT_FLAGGED"}:
            report_types.append("SAR")

        if sequence_result.get("sequence_pattern") in structured_patterns or self._contains_any_substring(trigger_reasons, ["STRUCTUR", "SMURF", "SMALL", "LAYERING"]):
            report_types.append("STR")

        if graph_mule_flag:
            report_types.append("MULE_ACCOUNT_ALERT")

        if decision == "REVIEW" or immediate_action == "REQUIRES_REVIEW" or decision_result.get("requires_human_intervention"):
            report_types.append("MANUAL_REVIEW_ESCALATION")

        deduped: List[str] = []
        for report_type in report_types:
            if report_type not in deduped:
                deduped.append(report_type)
        return deduped

    def _onboarding_report_types(self, decision_result: Mapping[str, Any], ml_output: Mapping[str, Any], control_result: Mapping[str, Any]) -> List[str]:
        report_types: List[str] = []
        decision = str(decision_result.get("decision", "")).upper()
        if decision == "BLOCK" or float(ml_output.get("ml_probability", 0.0)) >= 0.9:
            report_types.append("HIGH_RISK_ONBOARDING")
        if decision == "REVIEW" or decision_result.get("requires_review"):
            report_types.append("MANUAL_REVIEW_ESCALATION")
        if control_result.get("status") == "BLOCK":
            report_types.append("HIGH_RISK_ONBOARDING")
        deduped: List[str] = []
        for report_type in report_types:
            if report_type not in deduped:
                deduped.append(report_type)
        return deduped

    def generate_transaction_reports(
        self,
        txn: Mapping[str, Any],
        decision_result: Mapping[str, Any],
        control_result: Mapping[str, Any],
        ml_result: Mapping[str, Any],
        sequence_result: Mapping[str, Any],
        graph_result: Mapping[str, Any],
        evidence: Optional[Sequence[Mapping[str, Any]]] = None,
        source_engine: str = "TRANSACTION",
    ) -> List[Dict[str, Any]]:
        evidence_items = list(evidence or self._build_transaction_evidence(decision_result, ml_result, sequence_result, graph_result, control_result))
        report_types = self._transaction_report_types(decision_result, control_result, sequence_result, graph_result, ml_result)
        if not report_types:
            return []

        report_records: List[Dict[str, Any]] = []
        user_id = str(txn.get("sender_id") or txn.get("user_id") or "")
        transaction_id = str(txn.get("trans_id") or txn.get("transaction_id") or txn.get("id") or "")
        reasons = self._collect_reasons(
            control_result.get("reason"),
            control_result.get("reasons"),
            ml_result.get("reasons"),
            sequence_result.get("sequence_pattern"),
            graph_result.get("reasons"),
            decision_result.get("reasons"),
        )

        for report_type in report_types:
            record = {
                "report_type": report_type,
                "user_id": user_id,
                "transaction_id": transaction_id,
                "decision": decision_result.get("decision", ""),
                "final_score": decision_result.get("final_score", 0),
                "behavior_score": ml_result.get("behavior_score", 0),
                "sequence_score": sequence_result.get("sequence_score", 0),
                "graph_score": graph_result.get("graph_score", 0),
                "rule_score": decision_result.get("rule_score", 0),
                "officer_recommendation": decision_result.get("officer_recommendation", ""),
                "immediate_action": decision_result.get("immediate_action", ""),
                "reason": reasons[0] if reasons else "",
                "reasons": reasons,
                "amount": txn.get("amount", 0),
                "source_engine": source_engine,
                "escalation_level": decision_result.get("officer_recommendation", report_type),
                "review_status": "PENDING" if decision_result.get("requires_human_intervention") else "AUTO",
                "evidence": evidence_items,
                "evidence_items": evidence_items,
                "metadata": {
                    "control": control_result,
                    "ml": ml_result,
                    "sequence": sequence_result,
                    "graph": graph_result,
                },
            }
            report_records.append(self._write_report(record))

        return report_records

    def generate_onboarding_reports(
        self,
        user_id: str,
        decision_result: Mapping[str, Any],
        control_result: Mapping[str, Any],
        ml_output: Mapping[str, Any],
        context: Mapping[str, Any],
        evidence: Optional[Sequence[str]] = None,
        source_engine: str = "ONBOARDING",
    ) -> List[Dict[str, Any]]:
        evidence_items = [{"category": "ONBOARDING", "finding": item} for item in list(evidence or [])]
        report_types = self._onboarding_report_types(decision_result, ml_output, control_result)
        if not report_types:
            return []

        report_records: List[Dict[str, Any]] = []
        reasons = self._collect_reasons(evidence, control_result.get("reason"), ml_output.get("top_features"))

        for report_type in report_types:
            record = {
                "report_type": report_type,
                "user_id": user_id,
                "transaction_id": context.get("transaction_id", ""),
                "decision": decision_result.get("decision", ""),
                "final_score": ml_output.get("ml_probability", 0),
                "behavior_score": ml_output.get("ml_probability", 0),
                "sequence_score": 0,
                "graph_score": 0,
                "rule_score": 1.0 if control_result.get("status") == "BLOCK" else 0.0,
                "officer_recommendation": decision_result.get("officer_recommendation", ""),
                "immediate_action": decision_result.get("decision", ""),
                "reason": reasons[0] if reasons else "",
                "reasons": reasons,
                "amount": context.get("amount", 0),
                "source_engine": source_engine,
                "escalation_level": decision_result.get("officer_recommendation", report_type),
                "review_status": "PENDING" if decision_result.get("requires_review") else "AUTO",
                "evidence": evidence_items,
                "evidence_items": evidence_items,
                "metadata": {
                    "control": control_result,
                    "ml": ml_output,
                    "context": context,
                },
            }
            report_records.append(self._write_report(record))

        return report_records

    def generate_legacy_report(self, user_id: str, report_type: str, reason: str, amount: Any) -> Dict[str, Any]:
        record = {
            "report_type": report_type,
            "user_id": user_id,
            "transaction_id": "",
            "decision": "UNKNOWN",
            "final_score": 0,
            "behavior_score": 0,
            "sequence_score": 0,
            "graph_score": 0,
            "rule_score": 0,
            "officer_recommendation": "",
            "immediate_action": "",
            "reason": reason,
            "reasons": [reason],
            "amount": amount,
            "source_engine": "LEGACY",
            "escalation_level": report_type,
            "review_status": "AUTO",
            "evidence": [{"category": "LEGACY", "finding": reason}],
            "evidence_items": [{"category": "LEGACY", "finding": reason}],
            "metadata": {"legacy": True},
        }
        return self._write_report(record)

    def list_reports(
        self,
        report_types: Optional[Sequence[str]] = None,
        user_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        decision: Optional[str] = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 50,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        frame = self._load_reports_frame()
        if frame.empty:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        if report_types:
            frame = frame[frame["report_type"].isin(report_types)]
        if user_id:
            frame = frame[frame["user_id"].astype(str) == str(user_id)]
        if transaction_id:
            frame = frame[frame["transaction_id"].astype(str) == str(transaction_id)]
        if decision:
            frame = frame[frame["decision"].astype(str).str.upper() == str(decision).upper()]
        if from_date and "timestamp" in frame.columns:
            frame = frame[frame["timestamp"] >= from_date]
        if to_date and "timestamp" in frame.columns:
            frame = frame[frame["timestamp"] <= to_date]

        if sort_by in frame.columns:
            ascending = str(sort_order).lower() != "desc"
            frame = frame.sort_values(by=sort_by, ascending=ascending)

        total = int(len(frame))
        start = max(page - 1, 0) * page_size
        end = start + page_size
        items = frame.iloc[start:end].to_dict(orient="records")
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_review_queue(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        return self.list_reports(
            report_types=["MANUAL_REVIEW_ESCALATION", "HIGH_RISK_ONBOARDING", "SAR", "STR", "MULE_ACCOUNT_ALERT"],
            sort_by="timestamp",
            sort_order="desc",
            page=page,
            page_size=page_size,
        )


reporting_service = ReportingService()


def generate_report(user_id: str, report_type: str, reason: str, amount: Any):
    return reporting_service.generate_legacy_report(user_id, report_type, reason, amount)