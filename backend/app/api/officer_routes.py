from fastapi import APIRouter, HTTPException
from typing import Optional

from app.services.cases.case_repository import case_repository
from app.services.officer.officer_case_service import OfficerCaseService
from app.services.officer.manual_review_service import ManualReviewService
from app.services.officer.whitelist_override_service import WhitelistOverrideService
from app.services.officer.sar_service import SARService
from app.services.officer.alert_management_service import alert_management_service
from app.services.officer.account_operations_service import account_operations_service
from app.services.officer.case_operations_service import case_operations_service
from app.services.officer.sar_generation_service import sar_generation_service

router = APIRouter()

case_service = OfficerCaseService()
review_service = ManualReviewService()
whitelist_service = WhitelistOverrideService()
sar_service = SARService()


def _sync_alert_for_case(case_id: str, status: str, officer_id: str, **extra_fields):
    case = case_repository.get_case(case_id)
    if not case:
        return None

    alert_id = str(case.get("source_alert_id") or "").strip()
    if not alert_id:
        return None

    try:
        return alert_management_service.update_alert_status(
            alert_id,
            status,
            "transaction",
            assigned_officer=officer_id,
            assigned_officer_id=officer_id,
            case_id=case_id,
            **extra_fields,
        )
    except Exception:
        return None


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

    try:
        result = account_operations_service.freeze_account(
            user_id=user_id,
            freeze_type=payload.get("freeze_type", "DEBIT_FREEZE"),
            freeze_reason=payload.get("reason", ""),
            frozen_by=payload.get("officer_id", "OFFICER_UNKNOWN"),
            case_id=payload.get("case_id"),
        )
        if payload.get("case_id"):
            case_service.update_case_status(payload["case_id"], "FROZEN", payload.get("officer_id", "OFFICER_1"))
            _sync_alert_for_case(payload["case_id"], "ACCOUNT_FROZEN", payload.get("officer_id", "OFFICER_1"), freeze_type=payload.get("freeze_type", "DEBIT_FREEZE"))
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/escalate")
def escalate_case(payload: dict):
    case_id = payload.get("case_id")
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required")
    return case_service.update_case_status(case_id, "ESCALATED", payload.get("officer_id", "SUPERVISOR_1"))


@router.post("/sar")
def generate_sar(payload: dict):
    case_id = payload.get("case_id")
    if not case_id:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        result = sar_generation_service.generate_sar_from_case(
            case_id=case_id,
            generated_by=payload.get("officer_id", "OFFICER_UNKNOWN"),
            officer_notes=payload.get("notes", ""),
            filing_type=payload.get("filing_type", "INTERNAL"),
        )
        _sync_alert_for_case(case_id, "SAR_GENERATED", payload.get("officer_id", "OFFICER_UNKNOWN"), filing_type=payload.get("filing_type", "INTERNAL"))
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# =========================
# GET ALL CASES
# =========================
@router.get("/case/all")
def get_cases():
    return case_repository.list_cases()


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


# =========================
# ALERT OPERATIONS
# =========================

@router.post("/acknowledge/{alert_id}")
def acknowledge_alert(
    alert_id: str,
    payload: dict
):
    """Acknowledge alert - officer takes ownership for investigation"""
    try:
        officer_id = payload.get("officer_id", "OFFICER_UNKNOWN")
        alert_type = payload.get("alert_type", "transaction")
        
        result = alert_management_service.acknowledge_alert(
            alert_id=alert_id,
            officer_id=officer_id,
            alert_type=alert_type
        )
        return {"status": "SUCCESS", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/escalate/{alert_id}")
def escalate_alert(
    alert_id: str,
    payload: dict
):
    """Escalate alert to higher priority"""
    try:
        escalated_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        escalation_reason = payload.get("reason", "")
        alert_type = payload.get("alert_type", "transaction")
        
        result = alert_management_service.escalate_alert(
            alert_id=alert_id,
            escalated_by=escalated_by,
            escalation_reason=escalation_reason,
            alert_type=alert_type
        )
        return {"status": "SUCCESS", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/request-edd/{alert_id}")
def request_edd(
    alert_id: str,
    payload: dict
):
    """Request Enhanced Due Diligence for alert"""
    try:
        requested_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        required_documents = payload.get("required_documents", None)
        alert_type = payload.get("alert_type", "transaction")
        
        result = alert_management_service.request_edd(
            alert_id=alert_id,
            requested_by=requested_by,
            required_documents=required_documents,
            alert_type=alert_type
        )
        return {"status": "SUCCESS", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close/{alert_id}")
def close_alert(
    alert_id: str,
    payload: dict
):
    """Close alert - investigation complete"""
    try:
        closed_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        resolution = payload.get("resolution", "RESOLVED")
        remarks = payload.get("remarks", "")
        alert_type = payload.get("alert_type", "transaction")
        
        result = alert_management_service.close_alert(
            alert_id=alert_id,
            closed_by=closed_by,
            resolution=resolution,
            remarks=remarks,
            alert_type=alert_type
        )
        return {"status": "SUCCESS", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# ACCOUNT OPERATIONS
# =========================

@router.post("/accounts/freeze/{user_id}")
def freeze_user_account(
    user_id: str,
    payload: dict
):
    """Freeze user account"""
    try:
        if account_operations_service.is_account_frozen(user_id):
            raise HTTPException(status_code=409, detail="Account is already frozen")
        
        freeze_type = payload.get("freeze_type", "DEBIT_FREEZE")
        freeze_reason = payload.get("reason", "")
        frozen_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        
        result = account_operations_service.freeze_account(
            user_id=user_id,
            freeze_type=freeze_type,
            freeze_reason=freeze_reason,
            frozen_by=frozen_by
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/unfreeze/{user_id}")
def unfreeze_user_account(
    user_id: str,
    payload: dict
):
    """Unfreeze user account"""
    try:
        lift_reason = payload.get("reason", "")
        lifted_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        
        result = account_operations_service.unfreeze_account(
            user_id=user_id,
            lift_reason=lift_reason,
            lifted_by=lifted_by
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/whitelist/{user_id}")
def whitelist_user_account(
    user_id: str,
    payload: dict
):
    """Whitelist user account"""
    try:
        reason = payload.get("reason", "")
        whitelisted_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        
        result = account_operations_service.whitelist_account(
            user_id=user_id,
            reason=reason,
            whitelisted_by=whitelisted_by
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/status/{user_id}")
def get_account_status(user_id: str):
    """Get account status (freeze, whitelist, etc)"""
    try:
        status = account_operations_service.get_account_status(user_id)
        return {"status": "SUCCESS", "account": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# CASE OPERATIONS
# =========================

@router.post("/cases/close/{case_id}")
def close_case(
    case_id: str,
    payload: dict
):
    """Close case - investigation complete"""
    try:
        closed_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        resolution = payload.get("resolution", "RESOLVED")
        remarks = payload.get("remarks", "")
        
        result = case_operations_service.close_case(
            case_id=case_id,
            closed_by=closed_by,
            resolution=resolution,
            remarks=remarks
        )
        _sync_alert_for_case(case_id, "CLOSED", closed_by, resolution=resolution, remarks=remarks)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/reopen/{case_id}")
def reopen_case(
    case_id: str,
    payload: dict
):
    """Reopen closed case"""
    try:
        reopened_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        reason = payload.get("reason", "")
        
        result = case_operations_service.reopen_case(
            case_id=case_id,
            reopened_by=reopened_by,
            reason=reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# SAR GENERATION
# =========================

@router.post("/reports/generate-sar/case/{case_id}")
def generate_sar_from_case(
    case_id: str,
    payload: dict
):
    """Generate SAR from case"""
    try:
        generated_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        officer_notes = payload.get("notes", "")
        filing_type = payload.get("filing_type", "INTERNAL")
        
        result = sar_generation_service.generate_sar_from_case(
            case_id=case_id,
            generated_by=generated_by,
            officer_notes=officer_notes,
            filing_type=filing_type
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/generate-sar/alert/{alert_id}")
def generate_sar_from_alert(
    alert_id: str,
    payload: dict
):
    """Generate SAR from alert"""
    try:
        generated_by = payload.get("officer_id", "OFFICER_UNKNOWN")
        officer_notes = payload.get("notes", "")
        alert_type = payload.get("alert_type", "transaction")
        filing_type = payload.get("filing_type", "INTERNAL")
        
        result = sar_generation_service.generate_sar_from_alert(
            alert_id=alert_id,
            generated_by=generated_by,
            officer_notes=officer_notes,
            alert_type=alert_type,
            filing_type=filing_type
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/sar")
def list_sar_reports():
    """List all SAR reports"""
    try:
        reports = sar_generation_service.get_sar_reports()
        return {"status": "SUCCESS", "reports": reports, "count": len(reports)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/sar/{sar_id}")
def get_sar_report(sar_id: str):
    """Get specific SAR report"""
    try:
        report = sar_generation_service.get_sar_report(sar_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"SAR {sar_id} not found")
        return {"status": "SUCCESS", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))