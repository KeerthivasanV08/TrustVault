from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from app.core import storage_paths

logger = logging.getLogger(__name__)


class PolicyEngine:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or storage_paths.POLICY_RULES_PATH
        self._lock = Lock()
        self._policy: dict[str, Any] = self._default_policy()
        self._loaded = False
        self.reload()

    def _default_policy(self) -> dict[str, Any]:
        return {
            "version": "fallback",
            "onboarding": {
                "sanction_hit": {"enabled": True, "action": "BLOCK", "requires_review": True, "requires_edd": True},
                "rooted_device": {"enabled": True, "action": "BLOCK", "requires_review": True},
                "vpn": {"enabled": True, "action": "REVIEW", "requires_review": True},
                "sim_swap": {"enabled": True, "requires_review": True, "requires_edd": True},
                "face_match_min": 0.60,
            },
            "transaction": {
                "new_user_upi_limit": 5000,
                "upi_daily_limit": 100000,
                "pan_cash_threshold": 50000,
                "savings_sft_limit": 1000000,
                "current_sft_limit": 5000000,
                "ctr_limit": 1000000,
                "mule_hub_threshold": 3,
                "dormancy_days": 180,
                "geo_limit": 25000,
            },
        }

    def reload(self) -> None:
        with self._lock:
            policy = self._default_policy()
            try:
                if self.path.exists():
                    with self.path.open("r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        policy = self._merge(policy, loaded)
                        self._loaded = True
                        logger.info("Loaded policy rules version %s from %s", policy.get("version", "unknown"), self.path)
                    else:
                        logger.error("policy_rules.json did not contain an object; using safe defaults")
                        self._loaded = False
                else:
                    logger.error("policy_rules.json missing at %s; using safe defaults", self.path)
                    self._loaded = False
            except Exception as exc:
                logger.error("Failed to load policy_rules.json: %s", exc)
                self._loaded = False
            self._policy = policy

    def _merge(self, base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
                merged[key] = self._merge(dict(merged[key]), value)
            else:
                merged[key] = value
        return merged

    def get_policy_version(self) -> str:
        return str(self._policy.get("version", "fallback"))

    def is_enabled(self, path: str, default: bool = False) -> bool:
        value = self.get_threshold(path, default)
        if isinstance(value, bool):
            return value
        return bool(value if value is not None else default)

    def get_threshold(self, path: str, default: Any = None) -> Any:
        current: Any = self._policy
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return default
            current = current[part]
        return current

    def get_onboarding_rule(self, name: str) -> Any:
        return self.get_threshold(f"onboarding.{name}")

    def get_transaction_rule(self, name: str) -> Any:
        return self.get_threshold(f"transaction.{name}")

    def loaded(self) -> bool:
        return self._loaded


policy_engine = PolicyEngine()


def get_policy_engine() -> PolicyEngine:
    return policy_engine