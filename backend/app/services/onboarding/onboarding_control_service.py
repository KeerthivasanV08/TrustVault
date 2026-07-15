from app.core.policy_engine import get_policy_engine


class OnboardingControlService:

    def __init__(self):
        self.policy = get_policy_engine()

    def evaluate(self, data: dict):

        reasons = []

        requires_review = False
        requires_edd = False

        hard_block = False

        # ----------------------------------------
        # HARD BLOCKS
        # ----------------------------------------

        sanction_rule = self.policy.get_onboarding_rule("sanction_hit") or {}
        if sanction_rule.get("enabled", True) and data.get("sanction_hit", 0):

            hard_block = True

            reasons.append(
                "SANCTION_HIT"
            )

        rooted_rule = self.policy.get_onboarding_rule("rooted_device") or {}
        if rooted_rule.get("enabled", True) and data.get("root_status", 0):

            hard_block = True

            reasons.append(
                "ROOTED_DEVICE"
            )

        # ----------------------------------------
        # SOFT RISKS
        # ----------------------------------------

        risk_rules = [

            ("emulator_flag", "EMULATOR_DEVICE"),
            ("vpn_flag", "VPN_DETECTED"),
            ("vpn_hosting_flag", "HOSTING_PROVIDER_IP"),
            ("proxy_flag", "PROXY_USAGE"),
            ("tor_flag", "TOR_NETWORK_USAGE"),
            ("sim_swap_flag", "SIM_SWAP_DETECTED"),
            ("pep_hit", "PEP_CUSTOMER"),
        ]

        for field, reason in risk_rules:

            if data.get(field, 0):

                reasons.append(reason)

                requires_review = True

        # ----------------------------------------
        # FACE MATCH
        # ----------------------------------------

        if data.get("face_match_score", 1) < float(self.policy.get_onboarding_rule("face_match_min") or 0.60):

            reasons.append(
                "LOW_FACE_MATCH"
            )

            requires_review = True

        # ----------------------------------------
        # EDD TRIGGERS
        # ----------------------------------------

        sim_swap_rule = self.policy.get_onboarding_rule("sim_swap") or {}
        if data.get("pep_hit", 0):

            requires_edd = True

        if sim_swap_rule.get("enabled", True) and data.get("sim_swap_flag", 0):

            requires_edd = True

        # ----------------------------------------
        # FINAL
        # ----------------------------------------

        if hard_block:

            return {

                "status": "BLOCK",

                "requires_review": True,

                "requires_edd": requires_edd,

                "reasons": reasons
            }

        return {

            "status": "ALLOW",

            "requires_review": requires_review,

            "requires_edd": requires_edd,

            "reasons": reasons
        }