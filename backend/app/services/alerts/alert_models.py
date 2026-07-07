from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Alert(BaseModel):
    alert_id: str
    alert_type: str
    priority: str
    severity: str
    risk_score: float
    decision: Optional[str] = None
    requires_edd: Optional[bool] = False
    assigned_queue: Optional[str] = None
    assigned_officer: Optional[str] = None
    state: str = "OPEN"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class Case(BaseModel):
    case_id: str
    source_alert: str
    source_alerts: List[str]
    status: str = "OPEN"
    priority: str
    assigned_officer: Optional[str] = None
    evidence: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None


class SLARecord(BaseModel):
    alert_id: str
    priority: str
    sla_minutes: int
    created_at: datetime
    due_at: datetime
    breached: bool = False
