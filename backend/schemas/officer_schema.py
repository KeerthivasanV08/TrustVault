from pydantic import BaseModel
from typing import List, Optional


class CaseCreateRequest(BaseModel):
    txn_id: str
    sender_id: str
    risk_score: float
    evidence: List[str]


class CaseResolveRequest(BaseModel):
    case_id: str
    decision: str   # RELEASE / REJECT
    officer_id: str
    notes: Optional[str] = ""


class WhitelistRequest(BaseModel):
    user_id: str
    reason: str
    officer_id: str