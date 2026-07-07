import asyncio
import logging
from typing import Any, Dict

import pandas as pd

"""
Realtime transaction simulation for the demo AML console.

This engine is the autonomous live transaction generator used for:
- SSE transaction feed
- live alerts
- dashboard metrics
- graph updates
- officer/case workflows

It is intentionally separate from TransactionService, which handles manual/API-submitted transactions.
"""

from app.realtime.transaction_generator import generate_transaction
from app.realtime.transaction_memory_store import (
    append_transaction,
    append_graph_event,
    publish_event,
    DASHBOARD_METRICS,
)

from app.services.transaction.ml_behavior_service import MLBehaviorService
from app.services.transaction.sequence_model_service import SequenceModelService
from app.services.transaction.graph_feature_service import GraphFeatureService
from app.services.transaction.graph_service import GraphIntelligenceEngine
from app.services.transaction.decision_engine import DecisionEngine
from app.services.transaction.velocity_service import VelocityService

from app.services.alerts.alert_priority_service import evaluate_priority
from app.services.alerts.transaction_alert_service import create_transaction_alert

logger = logging.getLogger(__name__)

USER_TRANSACTION_HISTORY: Dict[str, list[Dict[str, Any]]] = {}

_behavior_service = MLBehaviorService()
_sequence_service = SequenceModelService()
_graph_service = GraphIntelligenceEngine()
_graph_store = GraphFeatureService()
_decision_engine = DecisionEngine()
_velocity_service = VelocityService()


def _score(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value if value is not None else default)
    except Exception:
        return default

    if result > 1:
        result = result / 100.0

    return max(0.0, min(result, 1.0))


def _build_velocity_context(txn: Dict[str, Any], velocity_row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rolling_24h_sum": velocity_row.get("rolling_24h_sum", 0),
        "txn_count_24h": txn.get("tx_count_24h", velocity_row.get("txn_count_24h", 0)),
        "drain_ratio": txn.get("drain_ratio", velocity_row.get("drain_ratio", 0)),
        "unique_counterparties_24h": txn.get(
            "unique_counterparties_24h",
            velocity_row.get("unique_counterparties_24h", txn.get("unique_receivers_7d", 1)),
        ),
        "round_number_ratio": velocity_row.get("round_number_ratio", 0),
        "near_threshold_count": txn.get("near_threshold_flag", velocity_row.get("near_threshold_count", 0)),
        "avg_holding_time_mins": velocity_row.get("avg_holding_time_mins", 0),
        "velocity_gradient": velocity_row.get("velocity_gradient", 0),
        "txn_velocity_1h": txn.get("txn_velocity_1h", velocity_row.get("txn_count_24h", 0)),
        "forwarding_delay_mins": txn.get("forwarding_delay_mins", 999),
        "fragmentation_score": txn.get("fragmentation_score", 0),
        "rapid_outbound_after_inbound": txn.get("rapid_outbound_after_inbound", txn.get("rapid_movement", 0)),
        "avg_tx_amount_7d": txn.get("avg_tx_amount_7d", txn.get("amount", 0)),
        "unique_receivers_7d": txn.get("unique_receivers_7d", 1),
        "days_since_last_tx": txn.get("days_since_last_tx", 0),
        "rapid_movement": txn.get("rapid_movement", 0),
        "pass_through_ratio": txn.get("pass_through_ratio", 0),
        "velocity_risk_score": txn.get("velocity_risk_score", 0),
    }


def _build_onboarding_context(txn: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "identity_trust_score": txn.get("identity_trust_score", 50),
        "device_trust_score": txn.get("device_trust_score", 50),
        "sim_binding_ok": txn.get("sim_binding_ok", int(bool(txn.get("is_sim_bound", True)))),
        "sim_swap_flag": txn.get("sim_swap_flag", 0),
        "vpn_flag": txn.get("vpn_flag", 0),
        "hosting_flag": txn.get("hosting_flag", 0),
        "city_mismatch_flag": txn.get("city_mismatch_flag", 0),
        "device_age_years": txn.get("device_age_years", 3),
        "account_age_days": txn.get("account_age_days", 365),
        "network_risk_score": txn.get("network_risk_score", 0.1),
    }


def _build_graph_context(txn: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "graph_score": txn.get("graph_score", 0),
        "known_fraud_neighbors": txn.get("known_fraud_neighbors", txn.get("known_fraud_connections", 0)),
        "cluster_size": txn.get("mule_cluster_size", 0),
        "inbound_sources": txn.get("inbound_sources", 0),
        "outbound_dest": txn.get("outbound_dest", 0),
        "rapid_account_cluster_flag": txn.get("rapid_account_cluster_flag", 0),
        "mule_cluster_flag": txn.get("mule_cluster_flag", 0),
    }


def _seed_sequence_history(sender: str, txn: Dict[str, Any]) -> None:
    """
    The LSTM needs enough history. For generated demo transactions, we seed coherent
    sender history using the same scenario inputs. This does not change the model;
    it only ensures the model receives a proper sequence window.
    """
    band = str(txn.get("scenario_risk_band", "LOW")).upper()

    target_len = {
        "LOW": 6,
        "P3": 10,
        "P2": 12,
        "P1": 14,
    }.get(band, 6)

    hist = USER_TRANSACTION_HISTORY.setdefault(sender, [])

    while len(hist) < target_len - 1:
        clone = dict(txn)
        clone["trans_id"] = f"{txn.get('trans_id')}-HIST-{len(hist)}"

        if band == "LOW":
            clone["amount"] = max(100, float(txn.get("amount", 0)) * 0.65)
            clone["txn_velocity_1h"] = max(1, int(txn.get("txn_velocity_1h", 1)) - 1)
            clone["drain_ratio"] = min(_score(txn.get("drain_ratio")), 0.25)
            clone["forwarding_delay_mins"] = max(300, int(txn.get("forwarding_delay_mins", 999)))
        elif band == "P3":
            clone["amount"] = float(txn.get("amount", 0)) * 0.85
            clone["txn_velocity_1h"] = max(4, int(txn.get("txn_velocity_1h", 4)) - 1)
            clone["drain_ratio"] = max(0.35, _score(txn.get("drain_ratio")) * 0.95)
            clone["forwarding_delay_mins"] = max(60, int(txn.get("forwarding_delay_mins", 120)))
        elif band == "P2":
            clone["amount"] = float(txn.get("amount", 0)) * 0.92
            clone["txn_velocity_1h"] = max(9, int(txn.get("txn_velocity_1h", 9)) - 1)
            clone["drain_ratio"] = max(0.60, _score(txn.get("drain_ratio")) * 0.98)
            clone["forwarding_delay_mins"] = min(45, int(txn.get("forwarding_delay_mins", 30)))
        else:
            clone["amount"] = float(txn.get("amount", 0)) * 0.96
            clone["txn_velocity_1h"] = max(20, int(txn.get("txn_velocity_1h", 20)) - 1)
            clone["drain_ratio"] = max(0.88, _score(txn.get("drain_ratio")) * 0.99)
            clone["forwarding_delay_mins"] = min(5, int(txn.get("forwarding_delay_mins", 3)))

        hist.append(clone)

    hist.append(txn)

    if len(hist) > 20:
        del hist[:-20]


def _apply_realtime_component_fallbacks(
    txn: Dict[str, Any],
    behavior_result: Dict[str, Any],
    sequence_result: Dict[str, Any],
    graph_result: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Keeps the decision engine unchanged.

    This only stabilizes realtime simulation when a component is unavailable,
    returns insufficient history, or returns a clearly underpowered value for
    the scenario inputs. This is needed because demo generation must produce
    visible P1/P2/P3 bands while still using the same final fusion formula.
    """
    band = str(txn.get("scenario_risk_band", "LOW")).upper()

    behavior_floor = _score(txn.get("fallback_behavior_score"))
    sequence_floor = _score(txn.get("fallback_sequence_score"))
    graph_floor = _score(txn.get("fallback_graph_score", txn.get("graph_score")))

    behavior_score = _score(behavior_result.get("behavior_score"))
    sequence_score = _score(sequence_result.get("sequence_score"))
    graph_score = _score(graph_result.get("neo4j_graph_score", graph_result.get("graph_score")))

    if band in {"P1", "P2", "P3"} and behavior_score < behavior_floor:
        behavior_result = {
            **behavior_result,
            "behavior_score": behavior_floor,
            "behavior_label": behavior_result.get("behavior_label") or "SIMULATION_FALLBACK",
            "reasons": list(behavior_result.get("reasons") or []) + ["Realtime scenario behavior fallback"],
        }

    insufficient_sequence = sequence_result.get("sequence_pattern") in {
        "INSUFFICIENT_HISTORY",
        "ERROR",
        None,
    }

    if band in {"P1", "P2", "P3"} and (insufficient_sequence or sequence_score < sequence_floor):
        sequence_result = {
            **sequence_result,
            "sequence_score": sequence_floor,
            "sequence_pattern": {
                "P1": "GATHER_SCATTER",
                "P2": "LAUNDERING_FLOW",
                "P3": "ELEVATED_ACTIVITY_SEQUENCE",
            }.get(band, "NONE"),
        }

    if band in {"P1", "P2", "P3"} and graph_score < graph_floor:
        graph_result = {
            **graph_result,
            "neo4j_graph_score": graph_floor,
            "graph_score": graph_floor,
            "known_fraud_neighbors": max(
                int(graph_result.get("known_fraud_neighbors") or 0),
                int(txn.get("known_fraud_neighbors", txn.get("known_fraud_connections", 0)) or 0),
            ),
            "community_risk": {
                "P1": "CRITICAL",
                "P2": "HIGH",
                "P3": "MEDIUM",
            }.get(band, graph_result.get("community_risk", "LOW")),
            "network_role": graph_result.get("network_role") or (
                "SINK_NODE" if band == "P1" else "BRIDGE_LAYER"
            ),
            "reasons": list(graph_result.get("reasons") or []) + ["Realtime scenario graph fallback"],
        }

    return behavior_result, sequence_result, graph_result


def _control_result_for(txn: Dict[str, Any], behavior_result: Dict[str, Any], sequence_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    P1 >= 0.92 is mathematically impossible without rule_score because:
    behavior 0.30 + sequence 0.25 + graph 0.20 = max 0.75.
    Therefore genuine P1 simulation scenarios must trigger the control layer.
    """
    band = str(txn.get("scenario_risk_band", "")).upper()

    behavior_score = _score(behavior_result.get("behavior_score"))
    sequence_score = _score(sequence_result.get("sequence_score"))

    if band == "P1" and behavior_score >= 0.85 and sequence_score >= 0.80:
        return {
            "status": "BLOCK",
            "reason": "Critical mule laundering pattern detected",
        }

    return {}


def _ui_decision_for_score(final_score: float) -> str:
    if final_score >= 0.92:
        return "BLOCK"
    if final_score >= 0.75:
        return "REVIEW"
    if final_score >= 0.50:
        return "MONITOR"
    return "ALLOW"


def _status_for_score(final_score: float) -> str:
    if final_score >= 0.92:
        return "BLOCKED"
    if final_score >= 0.75:
        return "IN_REVIEW"
    if final_score >= 0.50:
        return "MONITORING"
    return "CLEARED"


def _collect_signals(
    txn: Dict[str, Any],
    behavior_result: Dict[str, Any],
    sequence_result: Dict[str, Any],
    graph_result: Dict[str, Any],
    final_score: float,
) -> list[str]:
    signals: list[str] = []

    if txn.get("scenario_type"):
        signals.append(str(txn["scenario_type"]))

    if txn.get("scenario_variant"):
        signals.append(str(txn["scenario_variant"]))

    for label in txn.get("signals") or []:
        signals.append(str(label))

    for label in behavior_result.get("reasons") or []:
        signals.append(str(label).upper().replace(" ", "_"))

    sequence_pattern = sequence_result.get("sequence_pattern")
    if sequence_pattern and sequence_pattern not in {"NONE", "INSUFFICIENT_HISTORY", "ERROR"}:
        signals.append(str(sequence_pattern).upper())

    for label in graph_result.get("reasons") or []:
        signals.append(str(label).upper().replace(" ", "_"))

    if final_score >= 0.92:
        signals.extend(["CRITICAL_RISK", "URGENT_REVIEW"])
    elif final_score >= 0.75:
        signals.extend(["REVIEW_REQUIRED", "ELEVATED_RISK"])
    elif final_score >= 0.50:
        signals.extend(["MONITORING", "ELEVATED_ACTIVITY"])
    else:
        signals.append("CLEARED")

    output = []
    seen = set()

    for signal in signals:
        token = str(signal).strip().upper()
        if token and token not in seen:
            seen.add(token)
            output.append(token)

    return output or ["NORMAL_PATTERN"]


async def process_transaction(txn: Dict[str, Any]):
    try:
        sender = str(txn.get("sender_id"))

        _seed_sequence_history(sender, txn)

        velocity_row = _velocity_service.update_after_transaction(txn)
        velocity_context = _build_velocity_context(txn, velocity_row)
        onboarding_context = _build_onboarding_context(txn)
        graph_context = _build_graph_context(txn)

        beh_features = _behavior_service.build_features_from_context(
            txn,
            velocity_context,
            onboarding_context,
            graph_context,
        )

        behavior_result = _behavior_service.predict_behavior_risk(beh_features)

        df_hist = pd.DataFrame(USER_TRANSACTION_HISTORY.get(sender, []))

        sequence_result = _sequence_service.predict_sequence(
            df_hist,
            behavioral_score=float(behavior_result.get("behavior_score", 0) or 0),
        )

        graph_result = _graph_service.evaluate_graph_risk(sender, txn)

        behavior_result, sequence_result, graph_result = _apply_realtime_component_fallbacks(
            txn,
            behavior_result,
            sequence_result,
            graph_result,
        )

        control_result = _control_result_for(txn, behavior_result, sequence_result)

        decision = _decision_engine.calculate_final_decision(
            behavior_result=behavior_result,
            sequence_result=sequence_result,
            graph_result=graph_result,
            control_result=control_result,
            user_context={},
            txn=txn,
        )

        final_score = _score(decision.get("final_score"))
        priority_meta = evaluate_priority(final_score)

        ui_decision = _ui_decision_for_score(final_score)
        status = _status_for_score(final_score)
        priority = priority_meta.get("priority", "INFO")

        signals = _collect_signals(
            txn,
            behavior_result,
            sequence_result,
            graph_result,
            final_score,
        )

        requires_review = priority in {"P2", "P3"}
        requires_block = priority == "P1"
        requires_case = priority in {"P1", "P2"}

        result = {
            **txn,
            "decision": ui_decision,
            "engine_decision": decision.get("decision"),
            "priority": priority,
            "status": status,

            "risk": final_score,
            "final_score": final_score,

            "behavior_score": decision.get("behavior_score"),
            "behaviorScore": decision.get("behavior_score"),

            "sequence_score": decision.get("sequence_score"),
            "sequenceScore": decision.get("sequence_score"),

            "graph_score": decision.get("graph_score"),
            "graphScore": decision.get("graph_score"),
            "neo4j_graph_score": decision.get("neo4j_graph_score", decision.get("graph_score")),

            "rule_score": decision.get("rule_score"),

            "behavior_label": behavior_result.get("behavior_label"),
            "sequence_pattern": sequence_result.get("sequence_pattern"),
            "community_risk": graph_result.get("community_risk"),
            "network_role": graph_result.get("network_role"),
            "known_fraud_neighbors": graph_result.get("known_fraud_neighbors"),

            "signals": signals,
            "reasons": decision.get("reasons", []),

            "alert_type": "TRANSACTION_SUSPECT" if priority in {"P1", "P2", "P3"} else "TRANSACTION_MONITOR",
            "requires_review": requires_review,
            "requires_block": requires_block,
            "requires_case": requires_case,
            "sla_minutes": priority_meta.get("sla_minutes"),
            "escalation_minutes": priority_meta.get("escalation_minutes"),
            "queue": priority_meta.get("queue"),
            "severity": priority_meta.get("severity"),
        }

        append_transaction(result)

        if priority in {"P1", "P2", "P3"}:
            try:
                alert = create_transaction_alert(
                    {
                        **result,
                        "decision": decision.get("decision"),
                        "alert_type": result.get("alert_type"),
                    }
                )
                append_graph_event({"type": "alert", "payload": alert})
            except Exception:
                logger.exception("Failed to create transaction alert for txn %s", txn.get("trans_id"))

        DASHBOARD_METRICS["total_transactions"] = DASHBOARD_METRICS.get("total_transactions", 0) + 1

        if priority == "P1":
            DASHBOARD_METRICS["blocked_transactions"] = DASHBOARD_METRICS.get("blocked_transactions", 0) + 1

        if priority in {"P1", "P2"}:
            DASHBOARD_METRICS["high_risk_count"] = DASHBOARD_METRICS.get("high_risk_count", 0) + 1

        if priority in {"P2", "P3"}:
            DASHBOARD_METRICS["review_queue"] = DASHBOARD_METRICS.get("review_queue", 0) + 1

        try:
            _graph_store.record_transaction(result, decision, graph_result)
        except Exception:
            logger.exception("Failed to persist realtime transaction into Neo4j")

        await publish_event({"event": "transaction", "data": result})

        logger.debug(
            "Processed txn %s -> score=%s priority=%s decision=%s",
            txn.get("trans_id"),
            final_score,
            priority,
            ui_decision,
        )

        return result

    except Exception:
        logger.exception("Realtime processing failed for txn: %s", txn)
        return None


async def start_realtime_engine():
    logger.info("Starting realtime AML engine")

    while True:
        try:
            txn = generate_transaction()
            await process_transaction(txn)
        except Exception:
            logger.exception("Error in realtime engine loop")

        await asyncio.sleep(2.5)