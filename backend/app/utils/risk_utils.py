def risk_band(score: float):

    if score > 90:
        return "CRITICAL"
    elif score > 75:
        return "HIGH"
    elif score > 40:
        return "MEDIUM"
    return "LOW"