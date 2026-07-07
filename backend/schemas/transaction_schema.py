from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TransactionRequest(BaseModel):
    trans_id: Optional[str] = None
    sender_id: str
    receiver_id: str
    amount: float = Field(gt=0)
    device_id: str
    ip_address: Optional[str] = None
    payment_mode: str = "UPI"
    channel: str = "UPI"
    timestamp: Optional[datetime] = None
    location: Optional[str] = None
    is_cash: int = 0


class TransactionResponse(BaseModel):
    status: str
    score: float
    recommendation: str
    evidence: list[str]
    requires_intervention: bool