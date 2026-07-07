import random
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, Tuple
from zoneinfo import ZoneInfo

USERS = [f"U-{i:04d}" for i in range(1000, 1100)]
MERCHANTS = [f"M-{i:04d}" for i in range(2000, 2050)]
DEVICES = [f"D-{i:05d}" for i in range(30000, 30100)]
LOCATIONS = ["Mumbai", "Bengaluru", "Delhi", "Chennai", "Kolkata", "Hyderabad", "Pune"]
CHANNELS = ["UPI", "IMPS", "NEFT", "NETBANKING", "CARD"]
TX_TYPES = ["PAYMENT", "TRANSFER", "P2P", "BILL"]

NORMAL_SENDERS = USERS[0:30]
NORMAL_RECEIVERS = MERCHANTS[0:20] + USERS[30:40]

P3_SENDERS = USERS[40:55]
P3_RECEIVERS = MERCHANTS[20:32]

P2_SENDERS = USERS[55:70]
P2_RECEIVERS = MERCHANTS[32:42] + USERS[70:78]

P1_SENDERS = USERS[78:88]
P1_RECEIVERS = MERCHANTS[42:50] + USERS[88:100]

IST = ZoneInfo("Asia/Kolkata")

_SENDER_COUNTS = defaultdict(int)
_PAIR_COUNTS = defaultdict(int)
_BAND_POOL: list[str] = []


def _refill_band_pool() -> None:
    """
    Realtime demo ratio:
    INFO/NORMAL: 65%
    P3: 20%
    P2: 10%
    P1: 5%
    """
    global _BAND_POOL

    pool: list[str] = []
    pool.extend(["NORMAL"] * 65)
    pool.extend(["P3"] * 20)
    pool.extend(["P2"] * 10)
    pool.extend(["P1"] * 5)

    random.shuffle(pool)
    _BAND_POOL = pool


def _now_iso() -> str:
    return datetime.now(IST).isoformat()


def _pick(values: Iterable[str]) -> str:
    return random.choice(list(values))


def _bump_state(sender_id: str, receiver_id: str) -> Tuple[int, int]:
    _SENDER_COUNTS[sender_id] += 1
    pair_key = f"{sender_id}->{receiver_id}"
    _PAIR_COUNTS[pair_key] += 1
    return _SENDER_COUNTS[sender_id], _PAIR_COUNTS[pair_key]


def _avg(amount: float, spread: float = 0.18) -> float:
    return round(amount * random.uniform(1 - spread, 1 + spread), 2)


def _signal_list(*signals: str) -> list[str]:
    return [signal for signal in signals if signal]


def _base_transaction(
    *,
    sender: str,
    receiver: str,
    amount: float,
    device_id: str,
    location: str,
    channel: str,
    transaction_type: str,
    scenario_type: str,
    scenario_variant: str,
    scenario_risk_band: str,
    is_sim_bound: bool,
    time_to_pay_ms: int,
    txn_velocity_1h: int,
    drain_ratio: float,
    forwarding_delay_mins: int,
    balance_depletion_speed: float,
    amount_deviation: float,
    avg_tx_amount_7d: float,
    account_age_days: int,
    device_shared_count: int,
    ip_shared_count: int,
    graph_score: float,
    fallback_behavior_score: float,
    fallback_sequence_score: float,
    fallback_graph_score: float,
    identity_trust_score: float,
    device_trust_score: float,
    sim_binding_ok: int,
    sim_swap_flag: int,
    vpn_flag: int,
    hosting_flag: int,
    city_mismatch_flag: int,
    device_age_years: float,
    network_risk_score: float,
    known_fraud_connections: int,
    mule_cluster_size: int,
    inbound_sources: int,
    outbound_dest: int,
    rapid_account_cluster_flag: int,
    mule_cluster_flag: int,
    tx_count_24h: int,
    unique_receivers_7d: int,
    days_since_last_tx: int,
    high_value_txn: int,
    rapid_movement: int,
    pass_through_ratio: float,
    structuring_pattern: int,
    night_high_value_txn: int,
    velocity_risk_score: float,
    signals: Iterable[str],
) -> Dict:
    if scenario_risk_band == "P1":
        before = round(amount / max(drain_ratio, 0.01), 2)
        after = round(max(0.0, before - amount), 2)
    else:
        before = round(max(amount * random.uniform(1.5, 7.5), random.uniform(5000, 250000)), 2)
        after = round(max(0.0, before - amount), 2)

    receiver_after = round(random.uniform(1000, 800000), 2)
    sender_count, pair_count = _bump_state(sender, receiver)

    return {
        "trans_id": str(uuid.uuid4()),
        "sender_id": sender,
        "receiver_id": receiver,
        "amount": round(amount, 2),
        "currency": "INR",
        "transaction_type": transaction_type,
        "channel": channel,
        "sender_bal_before": before,
        "sender_bal_after": after,
        "receiver_bal_after": receiver_after,
        "timestamp": _now_iso(),
        "location": location,
        "is_sim_bound": bool(is_sim_bound),
        "is_sim_bound_at_tx": int(bool(is_sim_bound)),
        "device_id": device_id,
        "time_to_pay_ms": int(time_to_pay_ms),

        "scenario_type": scenario_type,
        "scenario_variant": scenario_variant,
        "scenario_risk_band": scenario_risk_band,

        "txn_velocity_1h": int(max(txn_velocity_1h, sender_count)),
        "drain_ratio": round(float(drain_ratio), 4),
        "forwarding_delay_mins": int(forwarding_delay_mins),
        "balance_depletion_speed": round(float(balance_depletion_speed), 4),
        "amount_deviation": round(float(amount_deviation), 4),
        "avg_tx_amount_7d": round(float(avg_tx_amount_7d), 2),

        "distance_from_1L_threshold": round(abs(100000 - amount), 2),
        "distance_from_50k_threshold": round(abs(50000 - amount), 2),
        "empty_account_flag": int(after <= max(1000, before * 0.05)),
        "is_night_tx": int(random.random() < (0.65 if scenario_risk_band in {"P1", "P2"} else 0.15)),
        "is_round_amount": int(amount % 1000 == 0),
        "near_threshold_flag": int(48000 <= amount <= 50000 or 95000 <= amount <= 100000),

        "account_age_days": int(account_age_days),
        "device_shared_count": int(device_shared_count),
        "ip_shared_count": int(ip_shared_count),

        "graph_score": round(float(graph_score), 4),
        "fallback_behavior_score": round(float(fallback_behavior_score), 4),
        "fallback_sequence_score": round(float(fallback_sequence_score), 4),
        "fallback_graph_score": round(float(fallback_graph_score), 4),

        "identity_trust_score": round(float(identity_trust_score), 2),
        "device_trust_score": round(float(device_trust_score), 2),
        "sim_binding_ok": int(sim_binding_ok),
        "sim_swap_flag": int(sim_swap_flag),
        "vpn_flag": int(vpn_flag),
        "hosting_flag": int(hosting_flag),
        "city_mismatch_flag": int(city_mismatch_flag),
        "device_age_years": round(float(device_age_years), 2),
        "network_risk_score": round(float(network_risk_score), 4),

        "known_fraud_connections": int(known_fraud_connections),
        "known_fraud_neighbors": int(known_fraud_connections),
        "mule_cluster_size": int(mule_cluster_size),
        "inbound_sources": int(inbound_sources),
        "outbound_dest": int(outbound_dest),
        "rapid_account_cluster_flag": int(rapid_account_cluster_flag),
        "mule_cluster_flag": int(mule_cluster_flag),

        "tx_count_24h": int(tx_count_24h),
        "unique_receivers_7d": int(unique_receivers_7d),
        "days_since_last_tx": int(days_since_last_tx),

        "high_value_txn": int(high_value_txn),
        "rapid_movement": int(rapid_movement),
        "rapid_outbound_after_inbound": int(rapid_movement),
        "pass_through_ratio": round(float(pass_through_ratio), 4),
        "structuring_pattern": int(structuring_pattern),
        "fragmentation_score": round(float(pass_through_ratio if structuring_pattern else amount_deviation), 4),
        "night_high_value_txn": int(night_high_value_txn),
        "velocity_risk_score": round(float(velocity_risk_score), 4),

        "signals": list(dict.fromkeys(str(signal) for signal in signals if signal)),
        "pair_repeat_count": pair_count,
    }


def generate_normal_transaction() -> Dict:
    sender = _pick(NORMAL_SENDERS)
    receiver = _pick(NORMAL_RECEIVERS)
    amount = round(random.uniform(100, 15000), 2)
    avg_tx = _avg(amount, 0.12)
    sender_count, _ = _bump_state(sender, receiver)

    return _base_transaction(
        sender=sender,
        receiver=receiver,
        amount=amount,
        device_id=_pick(DEVICES[0:25]),
        location=_pick(LOCATIONS),
        channel=_pick(["UPI", "CARD", "NETBANKING"]),
        transaction_type=_pick(TX_TYPES),
        scenario_type="NORMAL",
        scenario_variant="LOW_RISK_PAYMENT",
        scenario_risk_band="LOW",
        is_sim_bound=True,
        time_to_pay_ms=random.randint(350, 2000),
        txn_velocity_1h=random.randint(1, 3),
        drain_ratio=random.uniform(0.05, 0.30),
        forwarding_delay_mins=random.randint(300, 1440),
        balance_depletion_speed=amount / random.uniform(90, 240),
        amount_deviation=abs(amount - avg_tx) / max(avg_tx, 1),
        avg_tx_amount_7d=avg_tx,
        account_age_days=random.randint(240, 2400),
        device_shared_count=random.choice([0, 0, 1]),
        ip_shared_count=random.choice([0, 0, 1]),
        graph_score=random.uniform(0.05, 0.35),
        fallback_behavior_score=random.uniform(0.05, 0.35),
        fallback_sequence_score=random.uniform(0.00, 0.25),
        fallback_graph_score=random.uniform(0.05, 0.35),
        identity_trust_score=random.uniform(78, 98),
        device_trust_score=random.uniform(74, 96),
        sim_binding_ok=1,
        sim_swap_flag=0,
        vpn_flag=0,
        hosting_flag=0,
        city_mismatch_flag=0,
        device_age_years=random.uniform(2, 7),
        network_risk_score=random.uniform(0.02, 0.15),
        known_fraud_connections=0,
        mule_cluster_size=0,
        inbound_sources=random.randint(1, 2),
        outbound_dest=1,
        rapid_account_cluster_flag=0,
        mule_cluster_flag=0,
        tx_count_24h=min(sender_count, 3),
        unique_receivers_7d=random.randint(1, 4),
        days_since_last_tx=random.randint(0, 3),
        high_value_txn=0,
        rapid_movement=0,
        pass_through_ratio=random.uniform(0.04, 0.16),
        structuring_pattern=0,
        night_high_value_txn=0,
        velocity_risk_score=random.uniform(0.04, 0.16),
        signals=_signal_list("NORMAL_PATTERN", "LOW_VALUE_PAYMENT", "SIM_BOUND"),
    )


def generate_p3_monitor_transaction() -> Dict:
    sender = _pick(P3_SENDERS)
    receiver = _pick(P3_RECEIVERS)
    amount = round(random.uniform(15000, 45000), 2)
    avg_tx = _avg(amount, 0.22)
    sender_count, _ = _bump_state(sender, receiver)

    return _base_transaction(
        sender=sender,
        receiver=receiver,
        amount=amount,
        device_id=_pick(DEVICES[20:45]),
        location=_pick(LOCATIONS),
        channel=_pick(["UPI", "CARD", "IMPS"]),
        transaction_type=random.choice(["TRANSFER", "PAYMENT", "P2P"]),
        scenario_type="P3_MONITOR",
        scenario_variant="MILD_VELOCITY",
        scenario_risk_band="P3",
        is_sim_bound=random.choice([True, True, True, False]),
        time_to_pay_ms=random.randint(180, 1200),
        txn_velocity_1h=random.randint(4, 8),
        drain_ratio=random.uniform(0.35, 0.55),
        forwarding_delay_mins=random.randint(60, 240),
        balance_depletion_speed=amount / random.uniform(25, 80),
        amount_deviation=abs(amount - avg_tx) / max(avg_tx, 1),
        avg_tx_amount_7d=avg_tx,
        account_age_days=random.randint(90, 1500),
        device_shared_count=random.randint(1, 3),
        ip_shared_count=random.randint(0, 2),
        graph_score=random.uniform(0.35, 0.55),
        fallback_behavior_score=random.uniform(0.45, 0.65),
        fallback_sequence_score=random.uniform(0.35, 0.55),
        fallback_graph_score=random.uniform(0.35, 0.55),
        identity_trust_score=random.uniform(58, 84),
        device_trust_score=random.uniform(52, 80),
        sim_binding_ok=random.choice([1, 1, 1, 0]),
        sim_swap_flag=random.choice([0, 0, 0, 1]),
        vpn_flag=random.choice([0, 0, 1]),
        hosting_flag=0,
        city_mismatch_flag=random.choice([0, 0, 1]),
        device_age_years=random.uniform(1, 5),
        network_risk_score=random.uniform(0.18, 0.38),
        known_fraud_connections=random.choice([0, 0, 1]),
        mule_cluster_size=random.choice([0, 1, 2]),
        inbound_sources=random.randint(1, 3),
        outbound_dest=random.randint(1, 2),
        rapid_account_cluster_flag=0,
        mule_cluster_flag=0,
        tx_count_24h=max(sender_count, 4),
        unique_receivers_7d=random.randint(2, 5),
        days_since_last_tx=random.randint(0, 1),
        high_value_txn=int(amount >= 25000),
        rapid_movement=0,
        pass_through_ratio=random.uniform(0.20, 0.40),
        structuring_pattern=0,
        night_high_value_txn=random.choice([0, 0, 1]),
        velocity_risk_score=random.uniform(0.30, 0.50),
        signals=_signal_list("MILD_VELOCITY", "WATCHLIST_PROXIMITY", "DEVICE_REUSE"),
    )


def generate_structuring_transaction(risk_band: str = "P2") -> Dict:
    sender = _pick(P2_SENDERS if risk_band == "P2" else P1_SENDERS)
    receiver = _pick(P2_RECEIVERS if risk_band == "P2" else P1_RECEIVERS)

    amount = random.choice([48950, 49250, 49750, 98950, 99450]) + random.uniform(-60, 60)
    avg_tx = _avg(amount, 0.08)
    is_p1 = risk_band == "P1"

    return _base_transaction(
        sender=sender,
        receiver=receiver,
        amount=amount,
        device_id=_pick(DEVICES[45:90]),
        location=_pick(LOCATIONS),
        channel=_pick(["UPI", "NEFT", "IMPS"]),
        transaction_type="STRUCTURING",
        scenario_type="P1_CRITICAL" if is_p1 else "P2_REVIEW",
        scenario_variant="STRUCTURING",
        scenario_risk_band=risk_band,
        is_sim_bound=False if is_p1 else random.choice([True, False, False]),
        time_to_pay_ms=random.randint(10, 450),
        txn_velocity_1h=random.randint(20, 45) if is_p1 else random.randint(9, 18),
        drain_ratio=random.uniform(0.88, 0.99) if is_p1 else random.uniform(0.60, 0.80),
        forwarding_delay_mins=random.randint(0, 5) if is_p1 else random.randint(5, 45),
        balance_depletion_speed=amount / random.uniform(3, 12) if is_p1 else amount / random.uniform(8, 30),
        amount_deviation=abs(amount - avg_tx) / max(avg_tx, 1),
        avg_tx_amount_7d=avg_tx,
        account_age_days=random.randint(1, 60) if is_p1 else random.randint(5, 180),
        device_shared_count=random.randint(8, 20) if is_p1 else random.randint(3, 7),
        ip_shared_count=random.randint(5, 15) if is_p1 else random.randint(2, 6),
        graph_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        fallback_behavior_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.72, 0.88),
        fallback_sequence_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.66, 0.85),
        fallback_graph_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        identity_trust_score=random.uniform(5, 30) if is_p1 else random.uniform(30, 65),
        device_trust_score=random.uniform(5, 25) if is_p1 else random.uniform(28, 62),
        sim_binding_ok=0,
        sim_swap_flag=1,
        vpn_flag=1,
        hosting_flag=random.choice([0, 1]),
        city_mismatch_flag=1,
        device_age_years=random.uniform(0.1, 2.5),
        network_risk_score=random.uniform(0.70, 0.95) if is_p1 else random.uniform(0.45, 0.75),
        known_fraud_connections=random.randint(5, 15) if is_p1 else random.randint(2, 5),
        mule_cluster_size=random.randint(10, 30) if is_p1 else random.randint(3, 8),
        inbound_sources=random.randint(5, 12) if is_p1 else random.randint(3, 8),
        outbound_dest=random.randint(4, 10) if is_p1 else random.randint(2, 6),
        rapid_account_cluster_flag=1,
        mule_cluster_flag=1,
        tx_count_24h=random.randint(20, 45) if is_p1 else random.randint(9, 18),
        unique_receivers_7d=random.randint(5, 10) if is_p1 else random.randint(2, 6),
        days_since_last_tx=0,
        high_value_txn=1,
        rapid_movement=1,
        pass_through_ratio=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.60, 0.85),
        structuring_pattern=1,
        night_high_value_txn=1,
        velocity_risk_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        signals=_signal_list("STRUCTURING", "NEAR_THRESHOLD", "HIGH_VALUE_TRANSFER"),
    )


def generate_gather_scatter_transaction(risk_band: str = "P1") -> Dict:
    sender = _pick(P1_SENDERS if risk_band == "P1" else P2_SENDERS)
    receiver = _pick(P1_RECEIVERS if risk_band == "P1" else P2_RECEIVERS)
    is_p1 = risk_band == "P1"

    amount = round(random.uniform(95000, 450000), 2) if is_p1 else round(random.uniform(45000, 95000), 2)
    avg_tx = _avg(amount, 0.12)

    return _base_transaction(
        sender=sender,
        receiver=receiver,
        amount=amount,
        device_id=_pick(DEVICES[55:95]),
        location=_pick(LOCATIONS),
        channel=_pick(["IMPS", "NEFT", "UPI"]),
        transaction_type="GATHER_SCATTER",
        scenario_type="P1_CRITICAL" if is_p1 else "P2_REVIEW",
        scenario_variant="GATHER_SCATTER",
        scenario_risk_band=risk_band,
        is_sim_bound=False,
        time_to_pay_ms=random.randint(5, 220),
        txn_velocity_1h=random.randint(20, 45) if is_p1 else random.randint(9, 18),
        drain_ratio=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.60, 0.80),
        forwarding_delay_mins=random.randint(0, 5) if is_p1 else random.randint(5, 45),
        balance_depletion_speed=amount / random.uniform(3, 10) if is_p1 else amount / random.uniform(8, 28),
        amount_deviation=abs(amount - avg_tx) / max(avg_tx, 1),
        avg_tx_amount_7d=avg_tx,
        account_age_days=random.randint(1, 60) if is_p1 else random.randint(5, 180),
        device_shared_count=random.randint(8, 20) if is_p1 else random.randint(3, 7),
        ip_shared_count=random.randint(5, 15) if is_p1 else random.randint(2, 6),
        graph_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        fallback_behavior_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.72, 0.88),
        fallback_sequence_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.66, 0.85),
        fallback_graph_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        identity_trust_score=random.uniform(5, 30) if is_p1 else random.uniform(30, 65),
        device_trust_score=random.uniform(5, 25) if is_p1 else random.uniform(28, 62),
        sim_binding_ok=0,
        sim_swap_flag=1,
        vpn_flag=1,
        hosting_flag=random.choice([0, 1]),
        city_mismatch_flag=1,
        device_age_years=random.uniform(0.1, 2.5),
        network_risk_score=random.uniform(0.70, 0.95) if is_p1 else random.uniform(0.45, 0.75),
        known_fraud_connections=random.randint(5, 15) if is_p1 else random.randint(2, 5),
        mule_cluster_size=random.randint(10, 30) if is_p1 else random.randint(3, 8),
        inbound_sources=random.randint(6, 15) if is_p1 else random.randint(3, 8),
        outbound_dest=random.randint(5, 12) if is_p1 else random.randint(2, 6),
        rapid_account_cluster_flag=1,
        mule_cluster_flag=1,
        tx_count_24h=random.randint(20, 45) if is_p1 else random.randint(9, 18),
        unique_receivers_7d=random.randint(5, 12) if is_p1 else random.randint(2, 6),
        days_since_last_tx=0,
        high_value_txn=1,
        rapid_movement=1,
        pass_through_ratio=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.60, 0.85),
        structuring_pattern=0,
        night_high_value_txn=1,
        velocity_risk_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        signals=_signal_list("RAPID_DRAIN", "GATHER_SCATTER", "MULE_CLUSTER", "SIM_NOT_BOUND"),
    )


def generate_layering_transaction(risk_band: str = "P1") -> Dict:
    sender = _pick(P1_SENDERS if risk_band == "P1" else P2_SENDERS)
    receiver = _pick(P1_RECEIVERS if risk_band == "P1" else P2_RECEIVERS)
    is_p1 = risk_band == "P1"

    amount = round(random.uniform(95000, 450000), 2) if is_p1 else round(random.uniform(45000, 95000), 2)
    avg_tx = _avg(amount, 0.16)

    return _base_transaction(
        sender=sender,
        receiver=receiver,
        amount=amount,
        device_id=_pick(DEVICES[60:99]),
        location=_pick(LOCATIONS),
        channel=_pick(["NEFT", "IMPS", "UPI"]),
        transaction_type="LAYERING_STEP",
        scenario_type="P1_CRITICAL" if is_p1 else "P2_REVIEW",
        scenario_variant="LAYERING",
        scenario_risk_band=risk_band,
        is_sim_bound=False if is_p1 else random.choice([False, False, True]),
        time_to_pay_ms=random.randint(5, 280),
        txn_velocity_1h=random.randint(20, 45) if is_p1 else random.randint(9, 18),
        drain_ratio=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.60, 0.80),
        forwarding_delay_mins=random.randint(0, 5) if is_p1 else random.randint(5, 45),
        balance_depletion_speed=amount / random.uniform(3, 12) if is_p1 else amount / random.uniform(8, 30),
        amount_deviation=abs(amount - avg_tx) / max(avg_tx, 1),
        avg_tx_amount_7d=avg_tx,
        account_age_days=random.randint(1, 60) if is_p1 else random.randint(5, 180),
        device_shared_count=random.randint(8, 20) if is_p1 else random.randint(3, 7),
        ip_shared_count=random.randint(5, 15) if is_p1 else random.randint(2, 6),
        graph_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        fallback_behavior_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.72, 0.88),
        fallback_sequence_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.66, 0.85),
        fallback_graph_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        identity_trust_score=random.uniform(5, 30) if is_p1 else random.uniform(30, 65),
        device_trust_score=random.uniform(5, 25) if is_p1 else random.uniform(28, 62),
        sim_binding_ok=0,
        sim_swap_flag=1,
        vpn_flag=1,
        hosting_flag=random.choice([0, 1]),
        city_mismatch_flag=1,
        device_age_years=random.uniform(0.1, 2.5),
        network_risk_score=random.uniform(0.70, 0.95) if is_p1 else random.uniform(0.45, 0.75),
        known_fraud_connections=random.randint(5, 15) if is_p1 else random.randint(2, 5),
        mule_cluster_size=random.randint(10, 30) if is_p1 else random.randint(3, 8),
        inbound_sources=random.randint(5, 12) if is_p1 else random.randint(3, 8),
        outbound_dest=random.randint(5, 12) if is_p1 else random.randint(2, 6),
        rapid_account_cluster_flag=1,
        mule_cluster_flag=1,
        tx_count_24h=random.randint(20, 45) if is_p1 else random.randint(9, 18),
        unique_receivers_7d=random.randint(5, 12) if is_p1 else random.randint(2, 6),
        days_since_last_tx=0,
        high_value_txn=1,
        rapid_movement=1,
        pass_through_ratio=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.60, 0.85),
        structuring_pattern=0,
        night_high_value_txn=1,
        velocity_risk_score=random.uniform(0.90, 0.99) if is_p1 else random.uniform(0.70, 0.88),
        signals=_signal_list("LAYERING_CHAIN", "MULE_CLUSTER", "SHORT_FORWARDING_DELAY", "SIM_NOT_BOUND"),
    )


def generate_p2_review_transaction() -> Dict:
    roll = random.random()

    if roll < 0.34:
        return generate_structuring_transaction("P2")

    if roll < 0.67:
        return generate_layering_transaction("P2")

    return generate_gather_scatter_transaction("P2")


def generate_p1_critical_transaction() -> Dict:
    roll = random.random()

    if roll < 0.40:
        return generate_gather_scatter_transaction("P1")

    if roll < 0.75:
        return generate_layering_transaction("P1")

    return generate_structuring_transaction("P1")


def generate_transaction() -> Dict:
    global _BAND_POOL

    if not _BAND_POOL:
        _refill_band_pool()

    band = _BAND_POOL.pop()

    if band == "NORMAL":
        return generate_normal_transaction()

    if band == "P3":
        return generate_p3_monitor_transaction()

    if band == "P2":
        return generate_p2_review_transaction()

    return generate_p1_critical_transaction()