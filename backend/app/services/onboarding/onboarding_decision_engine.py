from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from app.services.shared.reporting_service import reporting_service


class OnboardingDecisionEngine:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        base = Path(__file__).resolve().parents[2]
        self.config_path = config_path or (base / "models" / "metadata" / "threshold_config.json")
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> dict:
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
        except Exception:
            pass
        return {"onboarding": {"block_threshold": 0.85, "review_threshold": 0.60}}

    def decide(
        self,
        control: dict,
        ml_output: dict,
        context: dict,
        evidence: Optional[Sequence[str]] = None,
    ):
        ml_probability = float(ml_output.get("ml_probability", 0.0))
        onboarding_thresholds = self.thresholds.get("onboarding", {})
        block_threshold = float(onboarding_thresholds.get("block_threshold", 0.85))
        review_threshold = float(onboarding_thresholds.get("review_threshold", 0.60))

        if control.get("status") == "BLOCK":
            decision_output = {
                "decision": "BLOCK",
                "requires_review": True,
                "requires_block": True,
                "requires_edd": control.get("requires_edd", False),
                "officer_recommendation": "Hard blocked by onboarding controls",
            }
        elif ml_probability >= block_threshold:
            decision_output = {
                "decision": "BLOCK",
                "requires_review": True,
                "requires_block": True,
                "requires_edd": True,
                "officer_recommendation": "High ML onboarding fraud probability",
            }
        elif ml_probability >= review_threshold:
            decision_output = {
                "decision": "REVIEW",
                "requires_review": True,
                "requires_block": False,
                "requires_edd": True,
                "officer_recommendation": "Manual onboarding review required",
            }
        elif context.get("vpn_flag", 0) and ml_probability >= 0.60:
            decision_output = {
                "decision": "REVIEW",
                "requires_review": True,
                "requires_block": False,
                "requires_edd": False,
                "officer_recommendation": "VPN + elevated ML risk",
            }
        else:
            decision_output = {
                "decision": "ALLOW",
                "requires_review": control.get("requires_review", False),
                "requires_block": False,
                "requires_edd": control.get("requires_edd", False),
                "officer_recommendation": "Approve onboarding",
            }

        report_records = []
        try:
            report_records = reporting_service.generate_onboarding_reports(
                user_id=str(context.get("user_id", "")),
                decision_result=decision_output,
                control_result=control,
                ml_output=ml_output,
                context=context,
                evidence=evidence,
                source_engine="ONBOARDING_DECISION_ENGINE",
            )
        except Exception:
            report_records = []

        decision_output["reports"] = report_records
        return decision_output