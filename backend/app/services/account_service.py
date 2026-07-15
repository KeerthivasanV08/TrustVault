from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.core import storage_paths
from app.core.storage_paths import DATA_DIR, PROCESSED_DIR


def _parse_bool(val: Any) -> Optional[bool]:
    if val is None or val == "":
        return None
    v = str(val).strip().lower()
    if v in ("1", "true", "t", "yes", "y"):
        return True
    if v in ("0", "false", "f", "no", "n"):
        return False
    return None


def _parse_float(val: Any) -> Optional[float]:
    try:
        if val is None or val == "":
            return None
        return float(val)
    except Exception:
        return None


def _parse_int(val: Any) -> Optional[int]:
    try:
        if val is None or val == "":
            return None
        return int(float(val))
    except Exception:
        return None


def _parse_date(val: Any) -> Optional[str]:
    if val is None or val == "":
        return None
    try:
        # try ISO parse
        dt = datetime.fromisoformat(str(val))
        return dt.isoformat()
    except Exception:
        # try common epoch millis
        try:
            ts = int(val)
            # assume seconds if small
            if ts > 1e12:
                # milliseconds
                return datetime.fromtimestamp(ts / 1000).isoformat()
            if ts > 1e9:
                return datetime.fromtimestamp(ts).isoformat()
        except Exception:
            return None
    return None


def _safe_str(s: Any) -> Optional[str]:
    if s is None:
        return None
    s2 = str(s).strip()
    return s2 if s2 != "" else None


@dataclass
class AccountService:
    users_csv: Path = DATA_DIR / "raw" / "users.csv"
    features_csv: Path = PROCESSED_DIR / "user_features.csv"
    onboarding_csv: Path = storage_paths.ONBOARDING_RISK_SNAPSHOT_PATH

    def _read_csv(self, path: Path) -> Iterable[Dict[str, Any]]:
        if not path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for r in reader:
                    rows.append(r)
        except Exception:
            return []
        return rows

    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        rows = self._read_csv(self.users_csv)
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            uid = _safe_str(r.get("user_id") or r.get("id"))
            if not uid:
                continue
            out[uid] = {
                "user_id": uid,
                "name": _safe_str(r.get("name") or r.get("customer_name") or f"Account {uid}"),
                "kyc_status": _safe_str(r.get("kyc_status")),
                "kyc_city": _safe_str(r.get("kyc_city")),
                "device_id": _safe_str(r.get("device_id")),
                "device_model_name": _safe_str(r.get("device_model_name")),
                "device_year": _parse_int(r.get("device_year")),
                "root_status": _parse_bool(r.get("root_status")),
                "app_cloner_flag": _parse_bool(r.get("app_cloner_flag")),
                "ip_address": _safe_str(r.get("ip_address")),
                "vpn_detected": _parse_bool(r.get("vpn_detected")),
                "isp_name": _safe_str(r.get("isp_name")),
                "registered_imsi": _safe_str(r.get("registered_imsi")),
                "current_imsi": _safe_str(r.get("current_imsi")),
                "sim_present": _parse_bool(r.get("sim_present")),
                "sim_slot_count": _parse_int(r.get("sim_slot_count")),
                "biometric_enabled": _parse_bool(r.get("biometric_enabled")),
                "onboarding_speed_ms": _parse_int(r.get("onboarding_speed_ms")),
                "created_at": _parse_date(r.get("created_at") or r.get("createdAt") or r.get("opened_at")),
            }
        return out

    def _load_features(self) -> Dict[str, Dict[str, Any]]:
        rows = self._read_csv(self.features_csv)
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            uid = _safe_str(r.get("user_id") or r.get("id"))
            if not uid:
                continue
            out[uid] = {
                "identity_trust_score": _parse_float(r.get("identity_trust_score")),
                "device_trust_score": _parse_float(r.get("device_trust_score")),
                "sim_binding_ok": _parse_int(r.get("sim_binding_ok")),
                "sim_swap_flag": _parse_int(r.get("sim_swap_flag")),
                "sim_age_days": _parse_int(r.get("sim_age_days")),
                "multi_sim_flag": _parse_int(r.get("multi_sim_flag")),
                "vpn_flag": _parse_int(r.get("vpn_flag")),
                "ip_risk_score": _parse_float(r.get("ip_risk_score")),
                "device_age_years": _parse_int(r.get("device_age_years")),
                "device_age_days": _parse_int(r.get("device_age_days")),
                "device_shared_count": _parse_int(r.get("device_shared_count")),
                "root_status": _parse_bool(r.get("root_status")),
                "emulator_flag": _parse_int(r.get("emulator_flag")),
                "app_cloner_flag": _parse_bool(r.get("app_cloner_flag")),
                "face_match_score": _parse_float(r.get("face_match_score")),
                "sanction_hit": _parse_int(r.get("sanction_hit")),
                "pep_hit": _parse_int(r.get("pep_hit")),
                "typing_speed": _parse_float(r.get("typing_speed")),
                "form_completion_time": _parse_float(r.get("form_completion_time")),
                "copy_paste_ratio": _parse_float(r.get("copy_paste_ratio")),
                "otp_retry_count": _parse_int(r.get("otp_retry_count")),
            }
        return out

    def _load_onboarding(self) -> Dict[str, Dict[str, Any]]:
        rows = self._read_csv(self.onboarding_csv)
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            uid = _safe_str(r.get("user_id") or r.get("id"))
            if not uid:
                continue
            out[uid] = {
                "final_risk_score": _parse_int(r.get("final_risk_score") or r.get("onboarding_risk_score")),
                "risk_level": _safe_str(r.get("risk_level")),
                "decision": _safe_str(r.get("decision")),
                "requires_review": _parse_bool(r.get("requires_review")),
                "requires_block": _parse_bool(r.get("requires_block")),
                "requires_edd": _parse_bool(r.get("requires_edd")),
                "reasons": _safe_str(r.get("reasons")),
                "confidence": _parse_float(r.get("confidence")),
                "officer_recommendation": _safe_str(r.get("officer_recommendation")),
            }
        return out

    def _merge_account(self, uid: str, users: Dict[str, Dict[str, Any]], feats: Dict[str, Dict[str, Any]], onboards: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        u = users.get(uid, {})
        f = feats.get(uid, {})
        o = onboards.get(uid, {})

        # prefer raw users for profile fields, features for ML fields
        account: Dict[str, Any] = {}
        account["user_id"] = uid
        account["name"] = u.get("name") or f"Account {uid}"
        account["kyc_status"] = u.get("kyc_status")
        account["kyc_city"] = u.get("kyc_city")
        account["created_at"] = u.get("created_at")
        account["device_id"] = u.get("device_id")
        account["device_model_name"] = u.get("device_model_name")
        account["device_year"] = u.get("device_year")
        account["root_status"] = u.get("root_status") if u.get("root_status") is not None else f.get("root_status")
        account["app_cloner_flag"] = u.get("app_cloner_flag") if u.get("app_cloner_flag") is not None else f.get("app_cloner_flag")
        account["ip_address"] = u.get("ip_address")
        account["vpn_detected"] = u.get("vpn_detected")
        account["isp_name"] = u.get("isp_name")
        account["registered_imsi"] = u.get("registered_imsi")
        account["current_imsi"] = u.get("current_imsi")
        account["sim_present"] = u.get("sim_present")
        account["sim_slot_count"] = u.get("sim_slot_count")
        account["biometric_enabled"] = u.get("biometric_enabled")
        account["onboarding_speed_ms"] = u.get("onboarding_speed_ms")

        # features
        account["identity_trust_score"] = f.get("identity_trust_score")
        account["device_trust_score"] = f.get("device_trust_score")
        account["sim_binding_ok"] = f.get("sim_binding_ok")
        account["sim_swap_flag"] = f.get("sim_swap_flag")
        account["sim_age_days"] = f.get("sim_age_days")
        account["multi_sim_flag"] = f.get("multi_sim_flag")
        account["vpn_flag"] = f.get("vpn_flag")
        account["ip_risk_score"] = f.get("ip_risk_score")
        account["device_age_years"] = f.get("device_age_years")
        account["device_age_days"] = f.get("device_age_days")
        account["device_shared_count"] = f.get("device_shared_count")
        account["emulator_flag"] = f.get("emulator_flag")
        account["face_match_score"] = f.get("face_match_score")
        account["sanction_hit"] = f.get("sanction_hit")
        account["pep_hit"] = f.get("pep_hit")
        account["typing_speed"] = f.get("typing_speed")
        account["form_completion_time"] = f.get("form_completion_time")
        account["copy_paste_ratio"] = f.get("copy_paste_ratio")
        account["otp_retry_count"] = f.get("otp_retry_count")

        # onboarding results
        account["onboarding_risk_score"] = o.get("final_risk_score")
        account["risk_level"] = o.get("risk_level")
        account["decision"] = o.get("decision")
        account["requires_review"] = o.get("requires_review")
        account["requires_block"] = o.get("requires_block")
        account["requires_edd"] = o.get("requires_edd")

        # explainability: build simple list from real fields
        explains: List[str] = []
        try:
            if account.get("sanction_hit") and int(account.get("sanction_hit") or 0) == 1:
                explains.append("Sanction screening hit detected")
        except Exception:
            pass
        try:
            if account.get("pep_hit") and int(account.get("pep_hit") or 0) == 1:
                explains.append("PEP escalation required")
        except Exception:
            pass
        if account.get("device_shared_count") is not None and account.get("device_shared_count") > 3:
            explains.append("Device reused across multiple accounts")
        if account.get("sim_swap_flag") and int(account.get("sim_swap_flag") or 0) == 1:
            explains.append("SIM swap risk detected")
        if account.get("sim_binding_ok") is not None and int(account.get("sim_binding_ok") or 0) == 0:
            explains.append("SIM binding mismatch detected")
        if account.get("vpn_flag") and int(account.get("vpn_flag") or 0) == 1 or account.get("vpn_detected"):
            explains.append("VPN detected during onboarding")
        if account.get("face_match_score") is not None and account.get("face_match_score") < 0.5:
            explains.append("Low face match score")
        if account.get("otp_retry_count") is not None and account.get("otp_retry_count") >= 3:
            explains.append("Multiple OTP retries observed")
        if account.get("emulator_flag") and int(account.get("emulator_flag") or 0) == 1:
            explains.append("Emulator environment detected")
        if account.get("root_status"):
            explains.append("Rooted device detected")
        if account.get("app_cloner_flag"):
            explains.append("App cloner detected")
        if account.get("ip_risk_score") is not None and account.get("ip_risk_score") > 60:
            explains.append("High-risk IP reputation")
        if account.get("multi_sim_flag") and int(account.get("multi_sim_flag") or 0) == 1:
            explains.append("Multiple SIM usage detected")

        account["explainability"] = explains

        # suspicious relationships: CSV doesn't provide graph relationships by default
        account["suspicious_relationships"] = []

        return account

    def _all_user_ids(self) -> List[str]:
        users = self._load_users()
        feats = self._load_features()
        onboards = self._load_onboarding()
        # union of keys across all CSV-backed data sources
        keys = set(users.keys()) | set(feats.keys()) | set(onboards.keys())
        # sort by created_at desc if available
        def key_fn(k: str):
            created = users.get(k, {}).get("created_at")
            if created:
                try:
                    return datetime.fromisoformat(created)
                except Exception:
                    return datetime.min
            return datetime.min

        return sorted(list(keys), key=key_fn, reverse=True)

    def search_accounts(self, search: Optional[str] = None, risk: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        users = self._load_users()
        feats = self._load_features()
        onboards = self._load_onboarding()

        ids = self._all_user_ids()
        results: List[Dict[str, Any]] = []

        # If search provided, search across several fields across full dataset
        if search:
            q = search.strip().lower()
            for uid in ids:
                u = users.get(uid, {})
                f = feats.get(uid, {})
                o = onboards.get(uid, {})
                hay = " ".join([
                    String(u.get("user_id") or ""),
                    String(u.get("device_id") or ""),
                    String(u.get("kyc_city") or ""),
                    String(u.get("device_model_name") or ""),
                    String(u.get("ip_address") or ""),
                    String(u.get("isp_name") or ""),
                    String(o.get("risk_level") or ""),
                    String(o.get("decision") or ""),
                    String(o.get("reasons") or ""),
                ]).lower()
                if q in hay:
                    results.append(self._merge_account(uid, users, feats, onboards))
        else:
            # default latest sorted by created_at desc
            for uid in ids:
                results.append(self._merge_account(uid, users, feats, onboards))

        # risk filtering
        if risk:
            r = risk.strip().upper()
            filtered: List[Dict[str, Any]] = []
            for acc in results:
                rl = (acc.get("risk_level") or "").upper() if acc.get("risk_level") else None
                if rl:
                    if rl == r:
                        filtered.append(acc)
                        continue
                # fallback derive from identity_trust_score or onboarding_risk_score
                score = None
                if acc.get("onboarding_risk_score") is not None:
                    try:
                        score = float(acc.get("onboarding_risk_score") or 0)
                    except Exception:
                        score = None
                elif acc.get("identity_trust_score") is not None:
                    try:
                        score = 100.0 - float(acc.get("identity_trust_score") or 0)
                    except Exception:
                        score = None
                if score is not None:
                    lvl = "LOW" if score < 33 else ("MEDIUM" if score < 66 else "HIGH")
                    if lvl == r:
                        filtered.append(acc)
            results = filtered

        # pagination
        total = len(results)
        sliced = results[offset: offset + limit]
        return {"total": total, "count": len(sliced), "offset": offset, "limit": limit, "results": sliced}

    def get_account(self, user_id: str) -> Optional[Dict[str, Any]]:
        users = self._load_users()
        feats = self._load_features()
        onboards = self._load_onboarding()
        if user_id not in users and user_id not in feats and user_id not in onboards:
            return None
        return self._merge_account(user_id, users, feats, onboards)
