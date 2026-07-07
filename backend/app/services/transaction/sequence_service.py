def detect_sequence_patterns(txn):

    patterns = []

    if txn["time_since_last_credit_ms"] < 120000:
        patterns.append(
            "RAPID_RELAY"
        )

    if txn["forwarding_delay_secs"] < 60:
        patterns.append(
            "INSTANT_FORWARDING"
        )

    return patterns