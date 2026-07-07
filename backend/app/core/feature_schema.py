from __future__ import annotations

from typing import Final

BEHAVIOR_CATEGORICAL_FEATURES: Final[list[str]] = [
    "transaction_type",
    "channel",
]

BEHAVIOR_NUMERIC_FEATURES: Final[list[str]] = [
    "amount",
    "sender_bal_before",
    "sender_bal_after",
    "receiver_bal_after",
    "is_sim_bound",
    "time_to_pay_ms",
    "amount_deviation",
    "balance_depletion_speed",
    "counterparty_diversity",
    "distance_from_1L_threshold",
    "distance_from_50k_threshold",
    "drain_ratio",
    "empty_account_flag",
    "forwarding_delay_mins",
    "fragmentation_score",
    "is_night_tx",
    "is_round_amount",
    "is_sim_bound_at_tx",
    "near_threshold_flag",
    "rapid_outbound_after_inbound",
    "txn_velocity_1h",
    "identity_trust_score",
    "device_trust_score",
    "sim_binding_ok",
    "sim_swap_flag",
    "vpn_flag",
    "hosting_flag",
    "city_mismatch_flag",
    "device_age_years",
    "graph_score",
    "known_fraud_connections",
    "mule_cluster_size",
    "inbound_sources",
    "outbound_dest",
    "rapid_account_cluster_flag",
    "mule_cluster_flag",
    "tx_count_24h",
    "avg_tx_amount_7d",
    "unique_receivers_7d",
    "days_since_last_tx",
    "account_age_days",
    "high_value_txn",
    "rapid_movement",
    "pass_through_ratio",
    "structuring_pattern",
    "night_high_value_txn",
    "velocity_risk_score",
    "network_risk_score",
]

BEHAVIOR_FEATURE_ORDER: Final[list[str]] = [
    *BEHAVIOR_NUMERIC_FEATURES,
    *BEHAVIOR_CATEGORICAL_FEATURES,
]

BEHAVIOR_SCHEMA: Final[dict[str, list[str]]] = {
    "features": BEHAVIOR_FEATURE_ORDER,
    "numerical_features": BEHAVIOR_NUMERIC_FEATURES,
    "categorical_features": BEHAVIOR_CATEGORICAL_FEATURES,
}

SEQUENCE_FEATURES: Final[list[str]] = [
    "amount",
    "drain_ratio",
    "txn_velocity_1h",
    "forwarding_delay_mins",
    "balance_depletion_speed",
]
