from fastapi import APIRouter, HTTPException
import pandas as pd

from app.services.officer.officer_case_service import OfficerCaseService, CASE_FILE
from app.services.officer.manual_review_service import ManualReviewService
from app.services.officer.whitelist_override_service import WhitelistOverrideService
from app.services.officer.freeze_service import FreezeService
from app.services.officer.sar_service import SARService

router = APIRouter()

case_service = OfficerCaseService()
review_service = ManualReviewService()
whitelist_service = WhitelistOverrideService()
freeze_service = FreezeService()
sar_service = SARService()


# =========================
# CREATE CASE (AUTO TRIGGER)
# =========================
@router.post("/case/create")
def create_case(payload: dict):

    case = case_service.create_case(
        txn_id=payload["txn_id"],
        sender_id=payload["sender_id"],
        evidence=payload.get("evidence", []),
        score=payload.get("risk_score", 0)
    )

    return case


@router.post("/review")
async def review_case(payload: dict):
    return await review_service.resolve_transaction(
        case_id=payload["case_id"],
        decision=payload.get("decision", "RELEASE"),
        officer_id=payload.get("officer_id", "OFFICER_1"),
        officer_notes=payload.get("notes", "")
    )


@router.post("/freeze")
def freeze_account(payload: dict):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    result = freeze_service.apply_freeze(user_id=user_id, freeze_type=payload.get("freeze_type", "TOTAL"))
    if payload.get("case_id"):
        case_service.update_case_status(payload["case_id"], "FROZEN", payload.get("officer_id", "OFFICER_1"))
    return result


@router.post("/escalate")
def escalate_case(payload: dict):
    case_id = payload.get("case_id")
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required")
    return case_service.update_case_status(case_id, "ESCALATED", payload.get("officer_id", "SUPERVISOR_1"))


@router.post("/sar")
def generate_sar(payload: dict):
    case_id = payload.get("case_id")
    if not case_id or not CASE_FILE.exists():
        raise HTTPException(status_code=404, detail="Case not found")

    df = pd.read_csv(CASE_FILE)
    rows = df[df["case_id"].astype(str) == str(case_id)]
    if rows.empty:
        raise HTTPException(status_code=404, detail="Case not found")

    case = rows.tail(1).iloc[0].to_dict()
    return sar_service.generate_sar_form(case, payload.get("notes", ""))


# =========================
# GET ALL CASES
# =========================
@router.get("/case/all")
def get_cases():
    if not CASE_FILE.exists():
        return []
    return pd.read_csv(CASE_FILE).to_dict("records")


# =========================
# RESOLVE CASE (OFFICER ACTION)
# =========================
@router.post("/case/resolve")
async def resolve_case(payload: dict):

    return await review_service.resolve_transaction(
        case_id=payload["case_id"],
        decision=payload["decision"],
        officer_id=payload.get("officer_id", "OFFICER_1"),
        officer_notes=payload.get("notes", "")
    )


# =========================
# WHITELIST USER
# =========================
@router.post("/whitelist")
def whitelist_user(payload: dict):

    return whitelist_service.add_to_whitelist(
        user_id=payload["user_id"],
        reason=payload.get("reason", "FALSE_POSITIVE"),
        officer_id=payload.get("officer_id", "OFFICER_1")
    )