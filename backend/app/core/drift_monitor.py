# backend/app/core/drift_monitor.py

def detect_hardware_drift(
    registered_device,
    current_device
):

    drift_score = 0

    if (
        registered_device.get("os_version")
        !=
        current_device.get("os_version")
    ):
        drift_score += 1

    if (
        registered_device.get("screen_resolution")
        !=
        current_device.get("screen_resolution")
    ):
        drift_score += 1

    if (
        registered_device.get("device_model")
        !=
        current_device.get("device_model")
    ):
        drift_score += 1

    return drift_score >= 2