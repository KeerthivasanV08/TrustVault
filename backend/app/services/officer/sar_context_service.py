from __future__ import annotations

import ast
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pandas as pd

from app.core import storage_paths
from app.core.policy_engine import get_policy_engine
from app.core.runtime_context import get_runtime_session_id
from app.realtime.transaction_memory_store import LIVE_ALERTS, get_recent_transactions
from app.services.alerts.alert_storage_service import read_csv
from app.services.alerts.investigator_assignment_service import get_investigator_profile
from app.services.cases.case_repository import case_repository
from app.services.onboarding.onboarding_context_service import OnboardingContextService
from app.services.shared.reporting_service import reporting_service
from app.services.transaction.audit_service import (
    EXPLAINABILITY_AUDIT_FILE,
    ML_AUDIT_FILE,
    OFFICER_AUDIT_FILE,
    TRANSACTION_AUDIT_FILE,
)
from app.services.transaction.context_service import ContextService
from app.services.transaction.graph_service import GraphIntelligenceEngine
from app.services.transaction.ml_behavior_service import MLBehaviorService
from app.services.transaction.sequence_model_service import SequenceModelService
from app.utils.risk_utils import risk_band


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
        return True
    return False


def _clean_text(value: Any, fallback: str = "") -> str:
    if _is_empty(value):
        return fallback
    text = str(value).strip()
    if text.lower() in {"none", "nan", "null"}:
        return fallback
    return text


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if _is_empty(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if _is_empty(value):
            return default
        number = float(value)
        return default if math.isnan(number) else number
    except Exception:
        return default


def _parse_datetime(value: Any) -> Optional[datetime]:
    if _is_empty(value):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            number = float(value)
            if number > 10_000_000_000:
                number /= 1000.0
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except Exception:
            return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _format_datetime(value: Any) -> str:
    parsed = _parse_datetime(value)
    return parsed.isoformat() if parsed else ""


def _parse_jsonish(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if _is_empty(value):
        return value
    text = str(value).strip()
    if not text:
        return value
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
            if isinstance(parsed, (dict, list, tuple, set, str, int, float, bool)):
                return parsed
        except Exception:
            continue
    return value


def _as_list(value: Any) -> List[str]:
    parsed = _parse_jsonish(value)
    if _is_empty(parsed):
        return []
    if isinstance(parsed, str):
        parts = [part.strip() for part in re.split(r"[\n\r;]+", parsed) if part.strip()]
        return parts or [parsed.strip()]
    if isinstance(parsed, Mapping):
        items = []
        for key in ("reasons", "reason", "findings", "items", "values"):
            if key in parsed:
                items.extend(_as_list(parsed.get(key)))
        return items
    if isinstance(parsed, Iterable):
        output: List[str] = []
        for item in parsed:
            if isinstance(item, Mapping):
                text = _clean_text(item.get("finding") or item.get("reason") or item.get("value") or item.get("text"), "")
            else:
                text = _clean_text(item, "")
            if text:
                output.append(text)
        return output
    text = _clean_text(parsed, "")
    return [text] if text else []


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    output: List[str] = []
    for value in values:
        cleaned = _clean_text(value, "")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
    return output


def _slugify_policy(reason: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", _clean_text(reason, "")).strip("_")
    return slug.upper()


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame()


class SARContextService:
    _frame_cache: Dict[str, pd.DataFrame] = {}

    def __init__(self) -> None:
        self.context = ContextService()
        self.onboarding = OnboardingContextService()
        self.policy = get_policy_engine()
        self._ml_service: MLBehaviorService | None = None
        self._sequence_service: SequenceModelService | None = None
        self._graph_service: GraphIntelligenceEngine | None = None

    def _ml(self) -> MLBehaviorService:
        if self._ml_service is None:
            self._ml_service = MLBehaviorService()
        return self._ml_service

    def _sequence(self) -> SequenceModelService:
        if self._sequence_service is None:
            self._sequence_service = SequenceModelService()
        return self._sequence_service

    def _graph(self) -> GraphIntelligenceEngine:
        if self._graph_service is None:
            self._graph_service = GraphIntelligenceEngine()
        return self._graph_service

    def _load_frame(self, path: Path) -> pd.DataFrame:
        cache_key = str(path)
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key].copy()

        if not path.exists():
            frame = _empty_frame()
        else:
            try:
                frame = pd.read_csv(path)
            except Exception:
                frame = _empty_frame()

        self._frame_cache[cache_key] = frame.copy()
        return frame

    def _find_first_record(self, frame: pd.DataFrame, identifiers: Mapping[str, Sequence[str]]) -> Dict[str, Any]:
        if frame.empty:
            return {}

        mask = pd.Series(False, index=frame.index)
        for column, values in identifiers.items():
            if column not in frame.columns:
                continue
            normalized = frame[column].astype(str).str.strip()
            mask = mask | normalized.isin([str(value).strip() for value in values if _clean_text(value, "")])

        matches = frame[mask]
        if matches.empty:
            return {}

        sort_column = next((column for column in ("timestamp", "generated_at", "updated_at", "created_at", "last_updated") if column in matches.columns), None)
        if sort_column:
            try:
                order = pd.to_datetime(matches[sort_column], errors="coerce", utc=True)
                matches = matches.assign(_sort_key=order).sort_values(by="_sort_key", ascending=False, na_position="last")
            except Exception:
                matches = matches.iloc[::-1]

        row = matches.iloc[0].to_dict()
        return {key: _parse_jsonish(value) for key, value in row.items()}

    def _find_case(self, case_id: str | None, alert_id: str | None = None) -> Dict[str, Any]:
        if not case_id and not alert_id:
            return {}

        cases = case_repository.list_cases()
        frame = pd.DataFrame(cases)
        if frame.empty:
            return {}

        identifiers: Dict[str, Sequence[str]] = {}
        if case_id:
            identifiers["case_id"] = [case_id]
        if alert_id:
            identifiers["source_alert_id"] = [alert_id]
        return self._find_first_record(frame, identifiers)

    def _find_alert(self, alert_id: str | None) -> Dict[str, Any]:
        if not alert_id:
            return {}

        normalized_alert_id = str(alert_id).strip()
        for live_alert in list(LIVE_ALERTS):
            if str(live_alert.get("alert_id", "")).strip() == normalized_alert_id:
                return {key: _parse_jsonish(value) for key, value in live_alert.items()}

        frames = []
        for key in ("transaction_alerts", "onboarding_alerts"):
            try:
                records = read_csv(key)
            except Exception:
                records = []
            if records:
                frames.append(pd.DataFrame(records))

        if not frames:
            return {}

        frame = pd.concat(frames, ignore_index=True, sort=False)
        return self._find_first_record(frame, {"alert_id": [alert_id]})

    def _find_transaction(self, transaction_id: str | None, user_id: str | None = None) -> Dict[str, Any]:
        recent = get_recent_transactions(limit=500, newest_first=True)
        if not recent:
            return {}

        frame = pd.DataFrame(recent)
        identifiers: Dict[str, Sequence[str]] = {}
        if transaction_id:
            identifiers["trans_id"] = [transaction_id]
            identifiers["transaction_id"] = [transaction_id]
            identifiers["id"] = [transaction_id]
        if user_id:
            identifiers["sender_id"] = [user_id]
            identifiers["user_id"] = [user_id]

        if not identifiers:
            return {}

        found = self._find_first_record(frame, identifiers)
        if found:
            return found

        if user_id:
            user_rows = frame[frame.get("sender_id", frame.get("user_id", pd.Series([], dtype=str))).astype(str).str.strip() == str(user_id).strip()]
            if not user_rows.empty:
                return {key: _parse_jsonish(value) for key, value in user_rows.iloc[0].to_dict().items()}

        return {}

    def _find_rows(self, path: Path, identifiers: Mapping[str, Sequence[str]]) -> List[Dict[str, Any]]:
        frame = self._load_frame(path)
        if frame.empty:
            return []
        matches = self._find_first_record(frame, identifiers)
        if not matches:
            return []
        return [matches]

    def _find_transaction_audit(self, transaction_id: str | None, user_id: str | None = None) -> Dict[str, Any]:
        frame = self._load_frame(TRANSACTION_AUDIT_FILE)
        if frame.empty:
            return {}
        identifiers: Dict[str, Sequence[str]] = {}
        if transaction_id:
            identifiers["transaction_id"] = [transaction_id]
        if user_id:
            identifiers["user_id"] = [user_id]
        return self._find_first_record(frame, identifiers)

    def _find_ml_audit(self, transaction_id: str | None) -> Dict[str, Any]:
        frame = self._load_frame(ML_AUDIT_FILE)
        if frame.empty or not transaction_id:
            return {}
        return self._find_first_record(frame, {"transaction_id": [transaction_id]})

    def _find_explainability_rows(self, transaction_id: str | None, user_id: str | None = None) -> List[Dict[str, Any]]:
        frame = self._load_frame(EXPLAINABILITY_AUDIT_FILE)
        if frame.empty:
            return []
        identifiers: Dict[str, Sequence[str]] = {}
        if transaction_id:
            identifiers["transaction_id"] = [transaction_id]
        if user_id:
            identifiers["user_id"] = [user_id]
        if not identifiers:
            return []
        if frame.empty:
            return []

        mask = pd.Series(False, index=frame.index)
        for column, values in identifiers.items():
            if column not in frame.columns:
                continue
            mask = mask | frame[column].astype(str).str.strip().isin([str(value).strip() for value in values if _clean_text(value, "")])
        matches = frame[mask]
        if matches.empty:
            return []
        if "timestamp" in matches.columns:
            try:
                matches = matches.assign(_sort_key=pd.to_datetime(matches["timestamp"], errors="coerce", utc=True)).sort_values(by="_sort_key", ascending=False, na_position="last")
            except Exception:
                matches = matches.iloc[::-1]
        return [{key: _parse_jsonish(value) for key, value in row.items()} for row in matches.to_dict(orient="records")]

    def _find_reports(self, case_id: str | None, alert_id: str | None, transaction_id: str | None) -> Dict[str, Any]:
        frame = self._load_frame(reporting_service.reports_path)
        if frame.empty:
            return {}

        identifiers: Dict[str, Sequence[str]] = {}
        if case_id:
            identifiers["case_id"] = [case_id]
        if alert_id:
            identifiers["alert_id"] = [alert_id]
        if transaction_id:
            identifiers["transaction_id"] = [transaction_id]

        if not identifiers:
            return {}

        return self._find_first_record(frame, identifiers)

    def _build_user_context(self, user_id: str) -> Dict[str, Any]:
        if not user_id:
            return {}
        user_context = dict(self.context.get_user_context(user_id) or {})
        velocity_context = dict(self.context.get_velocity_context(user_id) or {})
        onboarding_context = dict(self.context.get_onboarding_context(user_id) or {})

        user_context.setdefault("user_id", user_id)
        user_context.setdefault("account_id", _clean_text(user_context.get("account_id") or user_context.get("accountId") or user_id))

        account_age_days = _coerce_int(
            user_context.get("account_age_days")
            or onboarding_context.get("account_age_days")
            or onboarding_context.get("accountAgeDays")
            or velocity_context.get("account_age_days"),
            0,
        )
        if account_age_days > 0:
            user_context.setdefault("account_age_days", account_age_days)
            user_context.setdefault("account_age", f"{account_age_days} days")

        device_age_days = _coerce_int(
            user_context.get("device_age_days")
            or onboarding_context.get("device_age_days")
            or onboarding_context.get("deviceAgeDays"),
            0,
        )
        if device_age_days > 0:
            user_context.setdefault("device_age_days", device_age_days)
            user_context.setdefault("device_age", f"{device_age_days} days")

        sim_binding = user_context.get("sim_binding")
        if _is_empty(sim_binding):
            sim_binding = onboarding_context.get("sim_binding_ok")
        if not _is_empty(sim_binding):
            user_context.setdefault("sim_binding", sim_binding)

        vpn_flag = user_context.get("vpn_flag")
        if _is_empty(vpn_flag):
            vpn_flag = onboarding_context.get("vpn_flag")
        if not _is_empty(vpn_flag):
            user_context.setdefault("vpn_flag", vpn_flag)

        city_mismatch = user_context.get("city_mismatch")
        if _is_empty(city_mismatch):
            city_mismatch = user_context.get("city_mismatch_flag") or onboarding_context.get("city_mismatch_flag")
        if not _is_empty(city_mismatch):
            user_context.setdefault("city mismatch", city_mismatch)
            user_context.setdefault("city_mismatch", city_mismatch)

        ip_address = _clean_text(user_context.get("ip_address") or user_context.get("ip"), "")
        if ip_address:
            try:
                user_context.update(self.onboarding.get_ip_risk(ip_address))
            except Exception:
                pass

        device_id = _clean_text(user_context.get("device_id"), "")
        if device_id:
            try:
                user_context.update(self.onboarding.get_device_age(device_id))
            except Exception:
                pass

        user_context.update({k: v for k, v in velocity_context.items() if not _is_empty(v)})
        user_context.update({k: v for k, v in onboarding_context.items() if not _is_empty(v)})
        return user_context

    def _build_transaction_context(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        if not txn:
            return {}

        transaction_id = _clean_text(txn.get("trans_id") or txn.get("transaction_id") or txn.get("id"), "")
        sender_id = _clean_text(txn.get("sender_id") or txn.get("user_id") or txn.get("sender"), "")
        receiver_id = _clean_text(txn.get("receiver_id") or txn.get("receiver") or txn.get("to"), "")

        context = {
            "transaction_id": transaction_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "amount": txn.get("amount"),
            "currency": txn.get("currency"),
            "channel": txn.get("channel") or txn.get("payment_mode") or txn.get("payment_channel"),
            "location": txn.get("location") or txn.get("city") or txn.get("geo_location"),
            "timestamp": txn.get("timestamp") or txn.get("ts") or txn.get("created_at"),
            "scenario_type": txn.get("scenario_type") or txn.get("scenario") or txn.get("alert_type"),
            "scenario_variant": txn.get("scenario_variant"),
            "transaction_type": txn.get("transaction_type") or txn.get("txn_type") or txn.get("type"),
            "device_id": txn.get("device_id"),
            "ip_address": txn.get("ip_address") or txn.get("ip"),
            "account_id": txn.get("account_id") or sender_id,
            "risk_band": txn.get("scenario_risk_band") or txn.get("risk_band"),
            "txn_velocity_1h": txn.get("txn_velocity_1h"),
            "fragmentation_score": txn.get("fragmentation_score"),
            "pass_through_ratio": txn.get("pass_through_ratio"),
            "forwarding_delay": txn.get("forwarding_delay_mins") or txn.get("forwarding_delay"),
            "velocity_score": txn.get("velocity_risk_score") or txn.get("velocity_score"),
            "account_age_days": txn.get("account_age_days"),
        }

        if not _is_empty(context.get("account_age_days")):
            context["account_age"] = f"{_coerce_int(context['account_age_days'])} days"
        if not _is_empty(context.get("forwarding_delay")):
            context["forwarding_delay"] = context.get("forwarding_delay")

        return {key: value for key, value in context.items() if not _is_empty(value)}

    def _build_velocity_context(self, user_id: str, txn: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        velocity_context = dict(self.context.get_velocity_context(user_id) or {}) if user_id else {}
        if txn:
            velocity_context.setdefault("txn_velocity_1h", txn.get("txn_velocity_1h") or velocity_context.get("txn_count_24h"))
            velocity_context.setdefault("fragmentation_score", txn.get("fragmentation_score") or user_context.get("fragmentation_score"))
            velocity_context.setdefault("pass_through_ratio", txn.get("pass_through_ratio") or user_context.get("pass_through_ratio"))
            velocity_context.setdefault("forwarding_delay_mins", txn.get("forwarding_delay_mins") or user_context.get("forwarding_delay_mins"))

        velocity_score = user_context.get("velocity_risk_score") or txn.get("velocity_risk_score") or velocity_context.get("velocity_risk_score")
        if _is_empty(velocity_score):
            rolling_sum = _coerce_float(velocity_context.get("rolling_24h_sum"), 0.0)
            txn_count = _coerce_float(velocity_context.get("txn_count_24h"), 0.0)
            fragmentation = _coerce_float(velocity_context.get("fragmentation_score"), 0.0)
            if rolling_sum or txn_count or fragmentation:
                velocity_score = round((txn_count * 0.3) + (fragmentation * 0.3) + min(rolling_sum / 100000.0, 0.4), 4)

        result = {
            "velocity_score": velocity_score,
            "txn_velocity_1h": velocity_context.get("txn_velocity_1h") or txn.get("txn_velocity_1h"),
            "drain_ratio": velocity_context.get("drain_ratio") or txn.get("drain_ratio"),
            "forwarding_delay": velocity_context.get("forwarding_delay_mins") or txn.get("forwarding_delay_mins") or txn.get("forwarding_delay"),
            "fragmentation_score": velocity_context.get("fragmentation_score") or txn.get("fragmentation_score"),
            "pass_through_ratio": velocity_context.get("pass_through_ratio") or txn.get("pass_through_ratio"),
            "velocity_risk_score": velocity_context.get("velocity_risk_score") or velocity_score,
            "rolling_24h_sum": velocity_context.get("rolling_24h_sum"),
            "txn_count_24h": velocity_context.get("txn_count_24h"),
            "unique_counterparties_24h": velocity_context.get("unique_counterparties_24h"),
        }
        return {key: value for key, value in result.items() if not _is_empty(value)}

    def _build_behavior_context(self, txn: Dict[str, Any], user_context: Dict[str, Any], velocity_context: Dict[str, Any], graph_context: Dict[str, Any]) -> Dict[str, Any]:
        behavior_result: Dict[str, Any] = {}
        if txn:
            try:
                features = self._ml().build_features_from_context(txn, velocity_context, user_context, graph_context)
                behavior_result = self._ml().predict_behavior_risk(features)
            except Exception:
                behavior_result = {}

        result = {
            "behavior_score": behavior_result.get("behavior_score") or txn.get("behavior_score") or user_context.get("behavior_score"),
            "behavior_label": behavior_result.get("behavior_label") or txn.get("behavior_label"),
            "top_features": behavior_result.get("top_features") or txn.get("top_features") or [],
            "behavior_reasons": behavior_result.get("reasons") or txn.get("behavior_reasons") or [],
        }
        if _is_empty(result.get("behavior_score")) and not _is_empty(txn.get("behavior_score")):
            result["behavior_score"] = txn.get("behavior_score")
        return {key: value for key, value in result.items() if not _is_empty(value)}

    def _build_sequence_context(self, user_id: str, behavior_score: Any) -> Dict[str, Any]:
        recent_transactions = self.context.get_recent_transactions(user_id, limit=10) if user_id else []
        if not recent_transactions:
            return {}

        try:
            sequence_result = self._sequence().predict_sequence(pd.DataFrame(recent_transactions), behavioral_score=_coerce_float(behavior_score, 0.0))
        except Exception:
            sequence_result = {}

        return {
            "sequence_score": sequence_result.get("sequence_score"),
            "sequence_pattern": sequence_result.get("sequence_pattern"),
            "sequence_reasons": [sequence_result.get("sequence_pattern")] if sequence_result.get("sequence_pattern") else [],
        }

    def _build_graph_context(self, user_id: str, txn: Dict[str, Any]) -> Dict[str, Any]:
        if not user_id:
            return {}

        graph_result: Dict[str, Any] = {}
        try:
            graph_result = self._graph().evaluate_graph_risk(user_id, txn)
        except Exception:
            graph_result = {}

        result = {
            "graph_score": graph_result.get("graph_score") or graph_result.get("neo4j_graph_score"),
            "hop_distance": graph_result.get("fraud_hop_distance") or graph_result.get("hop_distance"),
            "community_risk": graph_result.get("community_risk"),
            "network_role": graph_result.get("network_role"),
            "known_fraud_connections": graph_result.get("known_fraud_neighbors") or graph_result.get("known_fraud_connections"),
            "cluster_size": graph_result.get("cluster_size") or graph_result.get("chain_count"),
            "exposure_type": graph_result.get("exposure_type"),
            "graph_reasons": graph_result.get("reasons") or [],
            "graph_confidence": graph_result.get("confidence"),
        }
        return {key: value for key, value in result.items() if not _is_empty(value)}

    def _build_onboarding_context(self, user_id: str, txn: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        onboarding_context = dict(self.context.get_onboarding_context(user_id) or {}) if user_id else {}
        account_id = _clean_text(user_context.get("account_id") or user_context.get("accountId") or txn.get("account_id") or user_id, "")
        device_id = _clean_text(user_context.get("device_id") or txn.get("device_id"), "")
        ip_address = _clean_text(user_context.get("ip_address") or txn.get("ip_address") or txn.get("ip"), "")

        ip_risk = self.onboarding.get_ip_risk(ip_address) if ip_address else {}
        device_age = self.onboarding.get_device_age(device_id) if device_id else {}

        sim_binding = user_context.get("sim_binding") or onboarding_context.get("sim_binding_ok") or txn.get("sim_binding_ok")
        vpn_flag = user_context.get("vpn_flag") if not _is_empty(user_context.get("vpn_flag")) else onboarding_context.get("vpn_flag")
        city_mismatch = user_context.get("city_mismatch") or user_context.get("city_mismatch_flag") or onboarding_context.get("city_mismatch_flag") or txn.get("city_mismatch_flag")

        result = {
            "account_id": account_id,
            "identity_trust_score": user_context.get("identity_trust_score") or onboarding_context.get("identity_risk") or onboarding_context.get("identity_trust_score"),
            "device_trust_score": onboarding_context.get("device_trust_score") or user_context.get("device_trust_score") or txn.get("device_trust_score"),
            "account_age_days": user_context.get("account_age_days") or onboarding_context.get("account_age_days") or txn.get("account_age_days"),
            "risk_band": user_context.get("risk_band") or onboarding_context.get("risk_band") or risk_band(_coerce_float(user_context.get("velocity_risk_score") or txn.get("velocity_risk_score") or 0, 0.0) * 100.0),
            "sim_binding": sim_binding,
            "vpn_flag": vpn_flag if not _is_empty(vpn_flag) else ip_risk.get("vpn_flag"),
            "device_age": device_age.get("device_age_days") or user_context.get("device_age") or txn.get("device_age"),
            "city mismatch": city_mismatch,
            "city_mismatch": city_mismatch,
            "account_status": user_context.get("account_status"),
            "device_id": device_id,
            "ip_address": ip_address,
            "vpn_hosting_flag": ip_risk.get("vpn_hosting_flag"),
            "proxy_flag": ip_risk.get("proxy_flag"),
            "tor_flag": ip_risk.get("tor_flag"),
            "ip_risk_score": ip_risk.get("ip_risk_score"),
            "country_risk_score": ip_risk.get("country_risk_score"),
        }

        if not _is_empty(result.get("account_age_days")):
            result["account_age"] = f"{_coerce_int(result['account_age_days'])} days"
        if not _is_empty(result.get("device_age")) and isinstance(result.get("device_age"), (int, float)):
            result["device_age"] = f"{_coerce_int(result['device_age'])} days"

        return {key: value for key, value in result.items() if not _is_empty(value)}

    def _build_officer_context(self, case: Dict[str, Any], alert: Dict[str, Any], user_id: str, generated_by: str, audit_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        assigned_officer_id = _clean_text(
            alert.get("assigned_officer_id")
            or case.get("assigned_officer_id")
            or case.get("assigned_officer")
            or generated_by,
            "",
        )
        assigned_profile = get_investigator_profile(assigned_officer_id) if assigned_officer_id else {}
        assigned_officer_name = _clean_text(
            alert.get("assigned_officer_name")
            or case.get("assigned_officer_name")
            or assigned_profile.get("assigned_officer_name")
            or alert.get("assigned_officer")
            or case.get("assigned_officer")
            or assigned_officer_id,
            "",
        )

        acknowledged_at = ""
        escalated_at = ""
        officer_remarks: List[str] = []
        for row in audit_rows:
            action = _clean_text(row.get("action"), "").upper()
            timestamp = _format_datetime(row.get("timestamp"))
            notes = _clean_text(row.get("notes") or row.get("reason"), "")
            if action in {"ACTION_ACKNOWLEDGED", "ACKNOWLEDGED", "ACK"} and timestamp:
                acknowledged_at = acknowledged_at or timestamp
            if "ESCALAT" in action and timestamp:
                escalated_at = escalated_at or timestamp
            if notes:
                officer_remarks.append(notes)

        if not officer_remarks:
            officer_remarks.extend(_as_list(case.get("reason")) or _as_list(alert.get("reason")))

        result = {
            "assigned_officer_id": assigned_officer_id,
            "assigned_officer_name": assigned_officer_name,
            "assigned_officer": assigned_officer_name,
            "assigned_at": _format_datetime(alert.get("assigned_at") or assigned_profile.get("last_assigned_at") or case.get("updated_at")),
            "acknowledged_at": acknowledged_at,
            "escalated_at": escalated_at,
            "officer_remarks": " | ".join(_dedupe(officer_remarks)),
        }

        if not result["officer_remarks"]:
            result["officer_remarks"] = _clean_text(case.get("resolution") or alert.get("resolution") or generated_by, "")

        return {key: value for key, value in result.items() if not _is_empty(value)}

    def _build_policy_context(
        self,
        case: Dict[str, Any],
        alert: Dict[str, Any],
        transaction: Dict[str, Any],
        transaction_audit: Dict[str, Any],
        ml_audit: Dict[str, Any],
        explainability_rows: List[Dict[str, Any]],
        graph_context: Dict[str, Any],
        sequence_context: Dict[str, Any],
        behavior_context: Dict[str, Any],
        decision_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        policy_reasons = []
        policy_reasons.extend(_as_list(transaction_audit.get("reason")))
        policy_reasons.extend(_as_list(transaction_audit.get("reasons")))
        policy_reasons.extend(_as_list(transaction_audit.get("rule_hits")))
        policy_reasons.extend(_as_list(decision_context.get("reasons")))

        control = _parse_jsonish(transaction_audit.get("rule_hits") or transaction_audit.get("reasons") or transaction_audit.get("reason"))
        control_list = _as_list(control)
        if not control_list:
            control_list = _as_list(alert.get("reason")) or _as_list(case.get("reason"))

        freeze_reason = _clean_text(
            case.get("freeze_status")
            or next((reason for reason in control_list if "FREEZE" in reason.upper() or "FROZEN" in reason.upper()), "")
            or next((row.get("finding") for row in explainability_rows if "FREEZE" in _clean_text(row.get("finding"), "").upper()), ""),
            "",
        )

        escalation_reason = _clean_text(
            case.get("escalation_level")
            or next((reason for reason in control_list if "ESCALAT" in reason.upper() or "REVIEW" in reason.upper()), "")
            or next((row.get("finding") for row in explainability_rows if "ESCALAT" in _clean_text(row.get("finding"), "").upper()), ""),
            "",
        )

        triggered_policy_names = [
            _slugify_policy(reason)
            for reason in policy_reasons
            if _slugify_policy(reason)
        ]
        if not triggered_policy_names and control_list:
            triggered_policy_names = [_slugify_policy(reason) for reason in control_list if _slugify_policy(reason)]

        violated_controls = _dedupe(control_list + _as_list(ml_audit.get("reasons")) + _as_list(graph_context.get("graph_reasons")) + _as_list(behavior_context.get("behavior_reasons")) + _as_list(sequence_context.get("sequence_reasons")))

        result = {
            "triggered_policy_names": triggered_policy_names,
            "violated_controls": violated_controls,
            "freeze_reason": freeze_reason,
            "escalation_reason": escalation_reason,
            "policy_version": self.policy.get_policy_version(),
            "policy_reasons": _dedupe(policy_reasons),
        }
        return {key: value for key, value in result.items() if not _is_empty(value)}

    def _build_decision_context(
        self,
        alert: Dict[str, Any],
        transaction: Dict[str, Any],
        transaction_audit: Dict[str, Any],
        ml_audit: Dict[str, Any],
        behavior_context: Dict[str, Any],
        sequence_context: Dict[str, Any],
        graph_context: Dict[str, Any],
        report_row: Dict[str, Any],
    ) -> Dict[str, Any]:
        final_score = (
            transaction_audit.get("risk_score")
            or report_row.get("final_score")
            or alert.get("risk_score")
            or transaction.get("final_score")
            or transaction.get("risk_score")
        )
        final_score = _coerce_float(final_score, 0.0)
        if final_score <= 1.0:
            risk_score = round(final_score * 100.0, 2)
        else:
            risk_score = round(final_score, 2)

        behavior_score = _coerce_float(
            ml_audit.get("behavior_score")
            or report_row.get("behavior_score")
            or behavior_context.get("behavior_score")
            or alert.get("behavior_score")
            or 0,
            0.0,
        )
        sequence_score = _coerce_float(
            ml_audit.get("sequence_score")
            or report_row.get("sequence_score")
            or sequence_context.get("sequence_score")
            or alert.get("sequence_score")
            or 0,
            0.0,
        )
        graph_score = _coerce_float(
            ml_audit.get("graph_score")
            or report_row.get("graph_score")
            or graph_context.get("graph_score")
            or alert.get("graph_score")
            or 0,
            0.0,
        )

        decision = _clean_text(
            transaction_audit.get("decision")
            or report_row.get("decision")
            or alert.get("decision")
            or transaction.get("decision")
            or "",
            "",
        )
        if not decision and risk_score:
            decision = "REVIEW" if risk_score >= 70 else "ALLOW"

        confidence_score = _coerce_float(
            alert.get("confidence")
            or report_row.get("confidence_score")
            or graph_context.get("graph_confidence")
            or transaction_audit.get("confidence")
            or 0,
            0.0,
        )

        reasons = _dedupe(
            _as_list(transaction_audit.get("reasons"))
            + _as_list(transaction_audit.get("reason"))
            + _as_list(transaction_audit.get("rule_hits"))
            + _as_list(ml_audit.get("reasons"))
            + _as_list(behavior_context.get("behavior_reasons"))
            + _as_list(sequence_context.get("sequence_reasons"))
            + _as_list(graph_context.get("graph_reasons"))
            + _as_list(report_row.get("reasons"))
            + _as_list(report_row.get("reason"))
        )

        return {
            "final_score": final_score,
            "risk_score": risk_score,
            "decision": decision,
            "final_decision": decision,
            "confidence_score": confidence_score,
            "behavior_score": behavior_score,
            "sequence_score": sequence_score,
            "graph_score": graph_score,
            "reasons": reasons,
            "reason": reasons[0] if reasons else "",
            "report_score": risk_score,
        }

    def _build_summary_context(
        self,
        transaction: Dict[str, Any],
        behavior_context: Dict[str, Any],
        sequence_context: Dict[str, Any],
        velocity_context: Dict[str, Any],
        graph_context: Dict[str, Any],
        onboarding_context: Dict[str, Any],
        policy_context: Dict[str, Any],
        decision_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        parts: List[str] = []

        velocity_score = _coerce_float(velocity_context.get("velocity_score") or velocity_context.get("velocity_risk_score") or 0, 0.0)
        if velocity_score or _coerce_float(velocity_context.get("txn_velocity_1h"), 0.0):
            if _coerce_float(velocity_context.get("txn_velocity_1h"), 0.0) >= 10 or _coerce_float(velocity_context.get("drain_ratio"), 0.0) >= 0.8:
                parts.append("High transaction velocity with rapid forwarding behaviour")

        if _coerce_float(graph_context.get("known_fraud_connections"), 0.0) > 0 or _clean_text(graph_context.get("community_risk"), "").upper() in {"HIGH", "CRITICAL"}:
            community = _clean_text(graph_context.get("community_risk"), "medium")
            parts.append(f"Connected to a {community.lower()}-risk mule cluster")

        sequence_pattern = _clean_text(sequence_context.get("sequence_pattern"), "")
        if sequence_pattern and sequence_pattern not in {"NONE", "INSUFFICIENT_HISTORY", "ERROR"}:
            parts.append(f"Sequence model identified {sequence_pattern.lower().replace('_', ' ')}")

        policy_reasons = _as_list(policy_context.get("violated_controls"))
        if policy_reasons:
            parts.append(f"Policy engine detected {policy_reasons[0].lower().replace('_', ' ')}")

        behavior_label = _clean_text(behavior_context.get("behavior_label"), "")
        if behavior_label and behavior_label not in {"UNKNOWN", "ALLOW"}:
            parts.append(f"Behavioral model classified the activity as {behavior_label.lower()}")

        if not parts and decision_context.get("reason"):
            parts.append(f"Decision basis: {decision_context.get('reason')}")

        if not parts:
            parts.append("Investigation context assembled from case, alert, transaction, and runtime audit sources")

        return {"investigation_summary": ". ".join(parts) + "."}

    def build_sar_context(
        self,
        case_id: str | None = None,
        alert_id: str | None = None,
        generated_by: str = "",
        officer_notes: str = "",
        filing_type: str = "INTERNAL",
        sar_id: str | None = None,
    ) -> Dict[str, Any]:
        case = self._find_case(case_id, alert_id)
        resolved_alert_id = _clean_text(alert_id or case.get("source_alert_id") or case.get("alert_id"), "")
        alert = self._find_alert(resolved_alert_id)

        if not case and resolved_alert_id:
            case = self._find_case(None, resolved_alert_id)

        if not case and alert.get("case_id"):
            case = self._find_case(_clean_text(alert.get("case_id"), ""), None)

        case_id = _clean_text(case_id or case.get("case_id") or case.get("id"), "")
        if not case_id and case.get("case_id"):
            case_id = _clean_text(case.get("case_id"), "")

        transaction_id = _clean_text(
            alert.get("transaction_id")
            or case.get("transaction_id")
            or case.get("source_transaction_id")
            or alert.get("trans_id")
            or "",
            "",
        )
        user_id = _clean_text(
            alert.get("user_id")
            or case.get("user_id")
            or alert.get("sender_id")
            or "",
            "",
        )

        transaction = self._find_transaction(transaction_id, user_id)
        if not transaction and user_id:
            history = self.context.get_recent_transactions(user_id, limit=1)
            if history:
                transaction = dict(history[0])

        if not transaction_id:
            transaction_id = _clean_text(transaction.get("trans_id") or transaction.get("transaction_id") or transaction.get("id"), "")
        if not user_id:
            user_id = _clean_text(transaction.get("sender_id") or transaction.get("user_id"), "")

        user_context = self._build_user_context(user_id) if user_id else {}
        transaction_context = self._build_transaction_context(transaction)
        alert_context = {
            "alert_id": _clean_text(alert.get("alert_id") or resolved_alert_id, ""),
            "alert_type": _clean_text(alert.get("alert_type") or case.get("source_type") or transaction.get("alert_type") or "transaction", "transaction"),
            "queue": _clean_text(alert.get("assigned_queue") or alert.get("queue") or case.get("assigned_team") or "", ""),
            "priority": _clean_text(alert.get("priority") or case.get("priority") or "", ""),
            "severity": _clean_text(alert.get("severity") or "", ""),
            "status": _clean_text(alert.get("status") or alert.get("state") or case.get("status") or "", ""),
            "investigation_status": _clean_text(alert.get("status") or alert.get("state") or case.get("status") or "", ""),
            "created_at": _format_datetime(alert.get("created_at") or case.get("created_at") or transaction.get("timestamp")),
            "updated_at": _format_datetime(alert.get("updated_at") or case.get("updated_at") or transaction.get("updated_at")),
            "sla_minutes": alert.get("sla_minutes") or alert.get("sla", {}).get("sla_minutes") if isinstance(alert.get("sla"), Mapping) else alert.get("sla_minutes"),
            "sla_due_at": _format_datetime(alert.get("sla_due_at") or (alert.get("sla", {}) or {}).get("due_at") if isinstance(alert.get("sla"), Mapping) else alert.get("sla_due_at")),
            "remaining_seconds": alert.get("remaining_seconds") or (alert.get("sla", {}) or {}).get("remaining_seconds") if isinstance(alert.get("sla"), Mapping) else alert.get("remaining_seconds"),
            "sla_breached": alert.get("sla_breached") or (alert.get("sla", {}) or {}).get("breached") if isinstance(alert.get("sla"), Mapping) else alert.get("sla_breached"),
            "decision": _clean_text(alert.get("decision") or transaction.get("decision") or case.get("status") or "", ""),
            "risk_score": alert.get("risk_score") or alert.get("final_score") or transaction.get("risk_score") or transaction.get("final_score"),
            "confidence": alert.get("confidence") or transaction.get("confidence") or user_context.get("confidence"),
            "metadata": _parse_jsonish(alert.get("metadata")) if alert.get("metadata") else {},
        }

        report_row = self._find_reports(case_id, resolved_alert_id, transaction_id)
        transaction_audit = self._find_transaction_audit(transaction_id, user_id)
        ml_audit = self._find_ml_audit(transaction_id)
        explainability_rows = self._find_explainability_rows(transaction_id, user_id)

        velocity_context = self._build_velocity_context(user_id, transaction, user_context) if user_id else {}
        onboarding_context = self._build_onboarding_context(user_id, transaction, user_context) if user_id else {}

        graph_context = self._build_graph_context(user_id, transaction) if user_id else {}
        behavior_context = self._build_behavior_context(transaction, user_context, velocity_context, graph_context) if transaction else {}
        sequence_context = self._build_sequence_context(user_id, behavior_context.get("behavior_score") or ml_audit.get("behavior_score") or report_row.get("behavior_score")) if user_id else {}

        if not behavior_context and ml_audit:
            behavior_context = {
                "behavior_score": ml_audit.get("behavior_score"),
                "behavior_label": ml_audit.get("behavior_label") or alert.get("behavior_label"),
                "top_features": _as_list(ml_audit.get("top_features") or report_row.get("metadata", {}).get("ml", {}).get("top_features") if isinstance(report_row.get("metadata"), Mapping) else []),
                "behavior_reasons": _as_list(ml_audit.get("reasons")),
            }

        decision_context = self._build_decision_context(alert, transaction, transaction_audit, ml_audit, behavior_context, sequence_context, graph_context, report_row)
        policy_context = self._build_policy_context(case, alert, transaction, transaction_audit, ml_audit, explainability_rows, graph_context, sequence_context, behavior_context, decision_context)
        officer_audit_rows = self._find_explainability_rows(transaction_id, user_id)
        officer_records_frame = self._load_frame(OFFICER_AUDIT_FILE)
        if not officer_records_frame.empty:
            officer_mask = pd.Series(False, index=officer_records_frame.index)
            for column, values in {"case_id": [case_id], "alert_id": [resolved_alert_id], "transaction_id": [transaction_id]}.items():
                if not column or not values or column not in officer_records_frame.columns:
                    continue
                officer_mask = officer_mask | officer_records_frame[column].astype(str).str.strip().isin([str(value).strip() for value in values if _clean_text(value, "")])
            officer_rows = officer_records_frame[officer_mask]
            if not officer_rows.empty:
                if "timestamp" in officer_rows.columns:
                    try:
                        officer_rows = officer_rows.assign(_sort_key=pd.to_datetime(officer_rows["timestamp"], errors="coerce", utc=True)).sort_values(by="_sort_key", ascending=False, na_position="last")
                    except Exception:
                        officer_rows = officer_rows.iloc[::-1]
                officer_audit_rows = [{key: _parse_jsonish(value) for key, value in row.items()} for row in officer_rows.to_dict(orient="records")]

        officer_context = self._build_officer_context(case, alert, user_id, generated_by, officer_audit_rows)
        summary_context = self._build_summary_context(transaction, behavior_context, sequence_context, velocity_context, graph_context, onboarding_context, policy_context, decision_context)

        resolved: Dict[str, Any] = {
            "title": "Suspicious Activity Report (SAR)",
            "sar_id": sar_id or f"SAR-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            "generated_by": generated_by,
            "generated_at": _now(),
            "officer_notes": officer_notes,
            "filing_type": filing_type,
            "runtime_session_id": get_runtime_session_id(),
            "metadata": {},
        }

        for section in (
            case,
            alert_context,
            transaction_context,
            user_context,
            behavior_context,
            sequence_context,
            velocity_context,
            graph_context,
            onboarding_context,
            officer_context,
            decision_context,
            policy_context,
            summary_context,
        ):
            for key, value in section.items():
                if not _is_empty(value):
                    resolved[key] = value

        resolved["case_id"] = _clean_text(case_id or resolved.get("case_id") or case.get("case_id") or "", "")
        resolved["alert_id"] = _clean_text(resolved_alert_id or resolved.get("alert_id") or alert.get("alert_id") or "", "")
        resolved["transaction_id"] = _clean_text(transaction_id or resolved.get("transaction_id") or transaction.get("trans_id") or transaction.get("transaction_id") or "", "")
        resolved["user_id"] = _clean_text(user_id or resolved.get("user_id") or transaction.get("sender_id") or transaction.get("user_id") or "", "")
        resolved["queue"] = _clean_text(resolved.get("queue") or alert.get("assigned_queue") or alert.get("queue") or case.get("assigned_team") or "", "")
        resolved["assigned_queue"] = resolved["queue"]

        if _is_empty(resolved.get("device_trust_score")):
            resolved["device_trust_score"] = alert.get("device_trust_score") or transaction.get("device_trust_score") or case.get("device_trust_score")

        if _is_empty(resolved.get("risk_score")) and not _is_empty(resolved.get("final_score")):
            resolved["risk_score"] = round(_coerce_float(resolved.get("final_score"), 0.0) * (100.0 if _coerce_float(resolved.get("final_score"), 0.0) <= 1.0 else 1.0), 2)
        if _is_empty(resolved.get("final_score")) and not _is_empty(resolved.get("risk_score")):
            score = _coerce_float(resolved.get("risk_score"), 0.0)
            resolved["final_score"] = round(score / 100.0 if score > 1.0 else score, 4)

        if _is_empty(resolved.get("confidence_score")):
            resolved["confidence_score"] = _coerce_float(behavior_context.get("behavior_score") or graph_context.get("graph_confidence") or alert.get("confidence") or 0, 0.0)

        if _is_empty(resolved.get("behavior_label")):
            resolved["behavior_label"] = "UNKNOWN"
        if _is_empty(resolved.get("sequence_pattern")):
            resolved["sequence_pattern"] = "INSUFFICIENT_HISTORY" if transaction else "UNKNOWN"
        if _is_empty(resolved.get("risk_band")):
            resolved["risk_band"] = risk_band(_coerce_float(resolved.get("risk_score"), 0.0))

        resolved["officer_notes"] = _clean_text(officer_notes or resolved.get("officer_notes") or resolved.get("officer_remarks") or case.get("resolution") or alert.get("reason") or "", "")
        resolved["officer_remarks"] = _clean_text(resolved.get("officer_remarks") or resolved["officer_notes"] or case.get("reason") or "", "")
        resolved["investigation_status"] = _clean_text(resolved.get("investigation_status") or resolved.get("status") or case.get("status") or alert.get("state") or "", "")
        resolved["created_at"] = resolved.get("created_at") or _format_datetime(case.get("created_at") or alert.get("created_at") or transaction.get("timestamp"))
        resolved["updated_at"] = resolved.get("updated_at") or _format_datetime(case.get("updated_at") or alert.get("updated_at") or transaction.get("updated_at"))
        resolved["generated_by"] = _clean_text(generated_by or resolved.get("generated_by") or alert.get("assigned_officer_id") or resolved.get("assigned_officer_id") or "", "")
        resolved["assigned_officer"] = _clean_text(resolved.get("assigned_officer") or resolved.get("assigned_officer_name") or resolved.get("assigned_officer_id") or generated_by or "", "")

        combined_reasons = _dedupe(
            _as_list(policy_context.get("policy_reasons"))
            + _as_list(policy_context.get("violated_controls"))
            + _as_list(behavior_context.get("behavior_reasons"))
            + _as_list(sequence_context.get("sequence_reasons"))
            + _as_list(graph_context.get("graph_reasons"))
            + _as_list(decision_context.get("reasons"))
            + _as_list(transaction_audit.get("reasons"))
            + _as_list(transaction_audit.get("reason"))
            + _as_list(ml_audit.get("reasons"))
            + _as_list(explainability_rows)
        )
        if combined_reasons:
            resolved["reasons"] = combined_reasons
            resolved["reason"] = combined_reasons[0]

        source_map = {
            "case": case,
            "alert": alert,
            "transaction": transaction,
            "report": report_row,
            "transaction_audit": transaction_audit,
            "ml_audit": ml_audit,
            "explainability_audit": explainability_rows,
            "user_context": user_context,
            "velocity_context": velocity_context,
            "onboarding_context": onboarding_context,
            "behavior_context": behavior_context,
            "sequence_context": sequence_context,
            "graph_context": graph_context,
            "officer_context": officer_context,
            "policy_context": policy_context,
            "decision_context": decision_context,
            "summary_context": summary_context,
        }
        resolved["metadata"] = {
            "generated_by": generated_by,
            "filing_type": filing_type,
            "sources": {name: source for name, source in source_map.items() if source},
            "report_row": report_row,
        }

        return resolved


sar_context_service = SARContextService()