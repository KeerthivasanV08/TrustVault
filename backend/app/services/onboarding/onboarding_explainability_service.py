class OnboardingExplainabilityService:
    def explain(self, context: dict, control: dict, ml_output: dict):
        reasons = []

        if context.get("sanction_hit", 0):
            reasons.append("Sanction list match detected")

        if context.get("pep_hit", 0):
            reasons.append("Politically exposed person escalation required")

        if context.get("vpn_flag", 0):
            reasons.append("VPN detected during onboarding")

        if context.get("hosting_flag", 0):
            reasons.append("Hosting provider IP detected")

        if context.get("proxy_flag", 0):
            reasons.append("Proxy IP detected")

        if context.get("tor_flag", 0):
            reasons.append("Tor network usage detected")

        if context.get("device_age_days", 0) < 2:
            reasons.append("New device detected")

        if context.get("root_status", 0):
            reasons.append("Rooted Android device detected")

        if context.get("emulator_flag", 0):
            reasons.append("Emulator device detected")

        if context.get("app_cloner_flag", 0):
            reasons.append("App cloner usage detected")

        if context.get("sim_swap_flag", 0):
            reasons.append("SIM swap risk detected")

        if context.get("sim_age_days", 0) < 2:
            reasons.append("SIM registered very recently")

        if context.get("face_match_score", 1) < 0.6:
            reasons.append("Face match confidence is low")

        if ml_output["identity_risk"] > 80:
            reasons.append("High ML identity risk score")

        # ml_top_features: list top model contributors as explainability reasons
        for feature in ml_output.get(
            "top_features",
            []
        ):
            reasons.append(
                f"ML elevated risk due to {feature}"
            )

        if control["status"] == "BLOCK":
            reasons.append("Blocked by onboarding control engine")

        if not reasons:
            reasons.append("No major onboarding risk indicators detected")

        return reasons