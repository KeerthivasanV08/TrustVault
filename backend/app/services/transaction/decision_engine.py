from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from app.services.shared.reporting_service import reporting_service

logger = logging.getLogger(__name__)


class DecisionEngine:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        base = Path(__file__).resolve().parents[2]
        self.config_path = config_path or (base / "models" / "metadata" / "threshold_config.json")
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> Dict[str, Any]:
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
        except Exception:
            logger.exception("Failed to load transaction decision thresholds")
        return {"transaction": {"auto_block": 0.92, "officer_review": 0.70, "soft_nudge": 0.50}}

    def _normalize_score(self, value: Any) -> float:
        try:
            score = float(value or 0)
        except Exception:
            return 0.0
        if score > 1.0:
            score = score / 100.0
        return max(0.0, min(score, 1.0))

    def calculate_final_decision(
        self,
        behavior_result: Mapping[str, Any],
        sequence_result: Mapping[str, Any],
        graph_result: Mapping[str, Any],
        control_result: Mapping[str, Any],
        user_context: Optional[Mapping[str, Any]] = None,
        txn: Optional[Mapping[str, Any]] = None,
        evidence: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        rule_score = 1.0 if str(control_result.get("status") or control_result.get("decision") or "").upper() == "BLOCK" else 0.0
        behavior_score = self._normalize_score(behavior_result.get("behavior_score", behavior_result.get("risk_score", 0)))
        sequence_score = self._normalize_score(sequence_result.get("sequence_score", 0))
        graph_score = self._normalize_score(graph_result.get("neo4j_graph_score", graph_result.get("graph_score", 0)))

        final_score = round(
            (behavior_score * 0.30)
            + (sequence_score * 0.25)
            + (graph_score * 0.20)
            + (rule_score * 0.25),
            4,
        )

        thresholds = self.thresholds.get("transaction", {})
        auto_block = float(thresholds.get("auto_block", 0.92))
        officer_review = float(thresholds.get("officer_review", 0.70))
        soft_nudge = float(thresholds.get("soft_nudge", 0.50))

        reasons = []
        reasons.extend([reason for reason in _as_list(control_result.get("reason") or control_result.get("reasons")) if reason])
        reasons.extend([reason for reason in _as_list(behavior_result.get("reasons")) if reason])
        sequence_pattern = sequence_result.get("sequence_pattern")
        if sequence_pattern and sequence_pattern not in {"NONE", "INSUFFICIENT_HISTORY", "ERROR"}:
            reasons.append(sequence_pattern)
        if graph_result.get("known_fraud_neighbors", 0) > 0:
            reasons.append("Connected to mule cluster")
        if graph_result.get("network_role") in {"COLLECTOR_HUB", "SINK_NODE", "BRIDGE_LAYER"}:
            reasons.append(f"Graph role {graph_result.get('network_role')}")

        if final_score >= auto_block or rule_score >= 1.0:
            decision = "BLOCK"
            immediate_action = "TRANSACTION_BLOCKED"
            officer_recommendation = "URGENT_BLOCK"
            requires_human = True
        elif final_score >= officer_review:
            decision = "REVIEW"
            immediate_action = "REQUIRES_REVIEW"
            officer_recommendation = "MANUAL_REVIEW_REQUIRED"
            requires_human = True
        elif final_score >= soft_nudge:
            decision = "SOFT_NUDGE"
            immediate_action = "ALLOW_WITH_NOTIFICATION"
            officer_recommendation = "SOFT_NUDGE"
            requires_human = False
        else:
            decision = "ALLOW"
            immediate_action = "APPROVED"
            officer_recommendation = "AUTO_PASS"
            requires_human = False

        report_records = []
        if txn is not None:
            try:
                report_records = reporting_service.generate_transaction_reports(
                    txn=txn,
                    decision_result={
                        "decision": decision,
                        "final_score": final_score,
                        "behavior_score": behavior_score,
                        "sequence_score": sequence_score,
                        "graph_score": graph_score,
                        "neo4j_graph_score": graph_score,
                        "rule_score": rule_score,
                        "officer_recommendation": officer_recommendation,
                        "immediate_action": immediate_action,
                        "requires_human_intervention": requires_human,
                        "reasons": reasons,
                    },
                    control_result=control_result,
                    ml_result=behavior_result,
                    sequence_result=sequence_result,
                    graph_result=graph_result,
                    evidence=evidence,
                    source_engine="TRANSACTION_DECISION_ENGINE",
                )
            except Exception:
                logger.exception("Failed to generate transaction reports")

        return {
            "decision": decision,
            "final_score": final_score,
            "behavior_score": behavior_score,
            "sequence_score": sequence_score,
            "graph_score": graph_score,
            "neo4j_graph_score": graph_score,
            "rule_score": rule_score,
            "reasons": reasons,
            "immediate_action": immediate_action,
            "officer_recommendation": officer_recommendation,
            "requires_human_intervention": requires_human,
            "reports": report_records,
        }


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]