import pandas as pd


class OnboardingFeatureBuilder:

    FEATURE_COLUMNS = [

        # ---------------------------------------------------
        # META FEATURES
        # ---------------------------------------------------

        "identity_trust_score",
        "device_trust_score",
        "behavioral_confidence",

        # ---------------------------------------------------
        # SIM / DEVICE
        # ---------------------------------------------------

        "sim_binding_ok",
        "sim_swap_flag",
        "sim_age_days",
        "multi_sim_flag",

        "device_age_years",
        "device_age_days",
        "device_shared_count",

        "root_status",
        "emulator_flag",
        "app_cloner_flag",

        # ---------------------------------------------------
        # NETWORK
        # ---------------------------------------------------

        "vpn_flag",
        "vpn_hosting_flag",
        "ip_risk_score",

        # ---------------------------------------------------
        # KYC
        # ---------------------------------------------------

        "face_match_score",
        "sanction_hit",
        "pep_hit",

        # ---------------------------------------------------
        # BEHAVIOR
        # ---------------------------------------------------

        "typing_speed",
        "form_completion_time",
        "copy_paste_ratio",
        "otp_retry_count",

        # ---------------------------------------------------
        # DERIVED SCORES
        # ---------------------------------------------------

        "sim_risk_score",
        "behavior_risk_score",

        # ---------------------------------------------------
        # DERIVED FLAGS
        # ---------------------------------------------------

        "high_copy_paste_flag",
        "old_device_flag",
        "otp_abuse_flag",

        # ---------------------------------------------------
        # RESIDUAL LEARNING META
        # ---------------------------------------------------

        "identity_trust_score_meta"
    ]

    def build_features(self, context: dict) -> pd.DataFrame:

        # ---------------------------------------------------
        # DEVICE FEATURES
        # ---------------------------------------------------

        device_shared_count = context.get(
            "device_shared_count", 0
        )

        emulator_flag = context.get(
            "emulator_flag", 0
        )

        device_age_days = context.get(
            "device_age_days", 0
        )

        device_age_years = round(
            device_age_days / 365,
            2
        )

        device_trust_score = max(

            0,

            min(
                100,

                100
                - device_shared_count * 10
                - emulator_flag * 40
            )
        )

        # ---------------------------------------------------
        # SIM RISK
        # ---------------------------------------------------

        sim_binding_ok = context.get(
            "sim_binding_ok", 1
        )

        sim_swap_flag = context.get(
            "sim_swap_flag", 0
        )

        multi_sim_flag = context.get(
            "multi_sim_flag", 0
        )

        sim_risk_score = (

            sim_swap_flag * 50

            + (1 - sim_binding_ok) * 30

            + multi_sim_flag * 20
        )

        # ---------------------------------------------------
        # BEHAVIOR RISK
        # ---------------------------------------------------

        typing_speed = context.get(
            "typing_speed", 50
        )

        copy_paste_ratio = context.get(
            "copy_paste_ratio", 0
        )

        otp_retry_count = context.get(
            "otp_retry_count", 0
        )

        behavior_risk_score = (

            (100 - typing_speed) * 0.3

            + copy_paste_ratio * 40

            + otp_retry_count * 10
        )

        behavioral_confidence = max(
            0,
            100 - behavior_risk_score
        )

        # ---------------------------------------------------
        # IDENTITY TRUST
        # ---------------------------------------------------

        face_match_score = context.get(
            "face_match_score", 0
        )

        identity_trust_score = (

            context.get("aadhaar_verified", 0) * 35

            + context.get("has_pan", 0) * 25

            + face_match_score * 40
        )

        # ---------------------------------------------------
        # DERIVED FLAGS
        # ---------------------------------------------------

        high_copy_paste_flag = int(
            copy_paste_ratio > 0.80
        )

        old_device_flag = int(
            device_age_days > 365 * 4
        )

        otp_abuse_flag = int(
            otp_retry_count >= 3
        )

        # ---------------------------------------------------
        # FINAL FEATURE ROW
        # ---------------------------------------------------

        row = {

            # META
            "identity_trust_score":
                identity_trust_score,

            "device_trust_score":
                device_trust_score,

            "behavioral_confidence":
                behavioral_confidence,

            # SIM
            "sim_binding_ok":
                sim_binding_ok,

            "sim_swap_flag":
                sim_swap_flag,

            "sim_age_days":
                context.get("sim_age_days", 0),

            "multi_sim_flag":
                multi_sim_flag,

            # DEVICE
            "device_age_years":
                device_age_years,

            "device_age_days":
                device_age_days,

            "device_shared_count":
                device_shared_count,

            "root_status":
                context.get("root_status", 0),

            "emulator_flag":
                emulator_flag,

            "app_cloner_flag":
                context.get("app_cloner_flag", 0),

            # NETWORK
            "vpn_flag":
                context.get("vpn_flag", 0),

            "vpn_hosting_flag":
                context.get("vpn_hosting_flag", 0),

            "ip_risk_score":
                context.get("ip_risk_score", 10),

            # KYC
            "face_match_score":
                face_match_score,

            "sanction_hit":
                context.get("sanction_hit", 0),

            "pep_hit":
                context.get("pep_hit", 0),

            # BEHAVIOR
            "typing_speed":
                typing_speed,

            "form_completion_time":
                context.get(
                    "form_completion_time",
                    60
                ),

            "copy_paste_ratio":
                copy_paste_ratio,

            "otp_retry_count":
                otp_retry_count,

            # DERIVED
            "sim_risk_score":
                sim_risk_score,

            "behavior_risk_score":
                behavior_risk_score,

            # FLAGS
            "high_copy_paste_flag":
                high_copy_paste_flag,

            "old_device_flag":
                old_device_flag,

            "otp_abuse_flag":
                otp_abuse_flag,

            # RESIDUAL LEARNING
            "identity_trust_score_meta":
                identity_trust_score
        }

        return pd.DataFrame(
            [row],
            columns=self.FEATURE_COLUMNS
        )