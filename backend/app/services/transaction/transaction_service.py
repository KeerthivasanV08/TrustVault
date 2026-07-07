from __future__ import annotations

import asyncio
from typing import Any, Mapping

import pandas as pd

from app.services.transaction.control_service import RegulatoryControlEngine
from app.services.transaction.ml_behavior_service import MLBehaviorService
from app.services.transaction.sequence_model_service import SequenceModelService
from app.services.transaction.graph_feature_service import GraphFeatureService
from app.services.transaction.graph_service import GraphIntelligenceEngine
from app.services.transaction.decision_engine import DecisionEngine
from app.services.shared.explainability_service import ExplainabilityService
from app.services.shared.reporting_service import reporting_service
from app.services.transaction.audit_service import AuditService
from app.services.transaction.whitelist_service import WhitelistService
from app.services.transaction.context_service import ContextService
from app.services.alerts.transaction_alert_service import create_transaction_alert

"""Manual/API transaction analysis pipeline.

TransactionService is the request-driven path used by POST /api/transactions
and /api/transactions/analyze. It scores a submitted transaction through the
feature, ML, graph, decision, explainability, audit, and alert layers. This is
distinct from app.realtime.realtime_engine, which generates live demo traffic
and streams it over SSE.
"""


class TransactionOrchestrator:
    def __init__(self):
        self.control = RegulatoryControlEngine()
        self.ml_behavior = MLBehaviorService()
        self.sequence = SequenceModelService()
        self.graph = GraphIntelligenceEngine()
        self.graph_store = GraphFeatureService()
        self.decision = DecisionEngine()
        self.explain = ExplainabilityService()
        self.audit = AuditService()
        self.whitelist = WhitelistService()
        self.context = ContextService()

    async def process_transaction(self, txn: Mapping[str, Any]):
        sender_id = str(txn.get("sender_id", ""))

        if self.whitelist.is_whitelisted(sender_id):
            return {
                "status": "APPROVED",
                "reason": "WHITELISTED_ENTITY",
                "requires_intervention": False,
                "reports": [],
            }

        control_result = self.control.evaluate(txn)

        if str(control_result.get("status") or control_result.get("decision") or "").upper() == "BLOCK":
            evidence = self.explain.generate_report(control_result, {}, {})
            hard_decision = {
                "decision": "BLOCK",
                "final_score": 1.0,
                "officer_recommendation": "URGENT_BLOCK",
                "immediate_action": "TRANSACTION_HALTED_ACCOUNT_FLAGGED",
                "requires_human_intervention": True,
                "reason": control_result.get("reason", "BLOCKED_BY_CONTROL_ENGINE"),
                "reasons": [control_result.get("reason", "BLOCKED_BY_CONTROL_ENGINE")],
            }
            reports = reporting_service.generate_transaction_reports(
                txn=txn,
                decision_result=hard_decision,
                control_result=control_result,
                ml_result={},
                sequence_result={"sequence_score": 0.0, "sequence_pattern": "INSUFFICIENT_HISTORY"},
                graph_result={"neo4j_graph_score": 0.0, "graph_score": 0.0, "known_fraud_neighbors": 0, "community_risk": "LOW", "reasons": []},
                evidence=evidence,
                source_engine="TRANSACTION_CONTROL_BLOCK",
            )
            self.audit.log_all(txn, hard_decision, evidence)
            return {
                "status": "TRANSACTION_BLOCKED",
                "recommendation": "URGENT_BLOCK",
                "score": 1.0,
                "evidence": evidence,
                "requires_intervention": True,
                "reports": reports,
            }

        user_context = self.context.get_user_context(sender_id)
        velocity_context = self.context.get_velocity_context(sender_id)
        onboarding_context = self.context.get_onboarding_context(sender_id)

        try:
            features_df = self.ml_behavior.build_features_from_context(txn, velocity_context, onboarding_context)
            ml_result = self.ml_behavior.predict_behavior_risk(features_df)
            ml_result.setdefault("reasons", [])
        except Exception:
            ml_result = {
                "behavior_score": 0.0,
                "behavior_label": "UNKNOWN",
                "top_features": [],
                "reasons": ["BEHAVIORAL_ENGINE_ERROR"],
            }

        try:
            graph_result = await asyncio.to_thread(self.graph.evaluate_graph_risk, sender_id, txn)
            graph_result.setdefault("reasons", [])
        except Exception:
            graph_result = {
                "neo4j_graph_score": 0.0,
                "graph_score": 0.0,
                "known_fraud_neighbors": 0,
                "community_risk": "UNKNOWN",
                "network_role": "UNKNOWN",
                "reasons": ["GRAPH_ENGINE_UNAVAILABLE"],
            }

        recent_transactions = self.context.get_recent_transactions(sender_id, limit=10)
        recent_df = pd.DataFrame(recent_transactions) if recent_transactions else pd.DataFrame()
        sequence_result = self.sequence.predict_sequence(
            recent_df,
            behavioral_score=float(ml_result.get("behavior_score", 0) or 0),
        )

        evidence = self.explain.generate_report(control_result, ml_result, graph_result)
        if sequence_result.get("sequence_pattern") not in {None, "NONE", "INSUFFICIENT_HISTORY", "ERROR"}:
            evidence.append({
                "category": "SEQUENCE",
                "finding": f"Sequence pattern: {sequence_result.get('sequence_pattern')}",
            })

        final_decision = self.decision.calculate_final_decision(
            behavior_result=ml_result,
            sequence_result=sequence_result,
            graph_result=graph_result,
            control_result=control_result,
            user_context=user_context,
            txn=txn,
            evidence=evidence,
        )

        self.audit.log_all(txn, final_decision, evidence)

        if str(final_decision.get("decision", "")).upper() in {"BLOCK", "REVIEW", "REQUIRES_REVIEW"} or float(final_decision.get("final_score", 0) or 0) >= 0.75:
            try:
                create_transaction_alert({
                    **dict(txn),
                    "final_score": final_decision.get("final_score", 0),
                    "behavior_score": final_decision.get("behavior_score", 0),
                    "sequence_score": final_decision.get("sequence_score", 0),
                    "graph_score": final_decision.get("graph_score", 0),
                    "neo4j_graph_score": final_decision.get("neo4j_graph_score", final_decision.get("graph_score", 0)),
                    "decision": final_decision.get("decision", final_decision.get("immediate_action", "REVIEW")),
                })
            except Exception:
                pass

        try:
            await asyncio.to_thread(
                self.graph_store.record_transaction,
                {
                    **dict(txn),
                    "behavior_score": final_decision.get("behavior_score", 0),
                    "sequence_score": final_decision.get("sequence_score", 0),
                    "graph_score": final_decision.get("graph_score", 0),
                    "neo4j_graph_score": final_decision.get("neo4j_graph_score", final_decision.get("graph_score", 0)),
                    "final_score": final_decision.get("final_score", 0),
                    "decision": final_decision.get("decision", "UNKNOWN"),
                },
                final_decision,
                graph_result,
            )
        except Exception:
            pass

        return {
            "status": final_decision.get("immediate_action"),
            "score": final_decision.get("final_score"),
            "recommendation": final_decision.get("officer_recommendation"),
            "evidence": evidence,
            "requires_intervention": final_decision.get("requires_human_intervention"),
            "reports": final_decision.get("reports", []),
            "scores": {
                "behavior": final_decision.get("behavior_score", 0),
                "sequence": final_decision.get("sequence_score", 0),
                "graph": final_decision.get("graph_score", 0),
                "neo4j_graph": final_decision.get("neo4j_graph_score", final_decision.get("graph_score", 0)),
                "rule": final_decision.get("rule_score", 0),
            },
        }


class TransactionService(TransactionOrchestrator):
    pass