from pydantic import BaseModel, Field
from typing import Optional


class OnboardingRequest(BaseModel):
    user_id: str
    ip_address: str
    device_id: str

    has_pan: int = 0
    aadhaar_verified: int = 0
    face_match_score: float = 0.0
    sanction_hit: int = 0
    pep_hit: int = 0

    root_status: int = 0
    emulator_flag: int = 0
    app_cloner_flag: int = 0
    device_shared_count: int = 0

    sim_imsi: Optional[str] = None
    sim_age_days: int = 0
    sim_binding_ok: int = 1
    sim_swap_flag: int = 0
    multi_sim_flag: int = 0

    typing_speed: float = 50.0
    form_completion_time: float = 60.0
    copy_paste_ratio: float = 0.0
    otp_retry_count: int = 0


class OnboardingResponse(BaseModel):
    user_id: str
    decision: str
    identity_risk: float
    confidence: float
    control_status: str
    reasons: list[str]