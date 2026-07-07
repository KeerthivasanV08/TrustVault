def calculate_confidence(
    feature_count,
    anomaly_count
):

    confidence = (
        0.5 +
        (feature_count * 0.03) +
        (anomaly_count * 0.05)
    )

    return min(confidence, 0.99)