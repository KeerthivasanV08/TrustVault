class OnboardingControlService:

    def evaluate(self, data: dict):

        reasons = []

        requires_review = False
        requires_edd = False

        hard_block = False

        # ----------------------------------------
        # HARD BLOCKS
        # ----------------------------------------

        if data.get("sanction_hit", 0):

            hard_block = True

            reasons.append(
                "SANCTION_HIT"
            )

        if data.get("root_status", 0):

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

        if data.get(
            "face_match_score",
            1
        ) < 0.60:

            reasons.append(
                "LOW_FACE_MATCH"
            )

            requires_review = True

        # ----------------------------------------
        # EDD TRIGGERS
        # ----------------------------------------

        if data.get("pep_hit", 0):

            requires_edd = True

        if data.get("sim_swap_flag", 0):

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