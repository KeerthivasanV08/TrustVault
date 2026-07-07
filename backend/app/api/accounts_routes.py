from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import md5
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.account_service import AccountService


router = APIRouter(tags=["Accounts"])


@router.get("")
async def list_accounts(limit: int = 50, search: str | None = None, risk: str | None = None, offset: int = 0):
    """Return merged accounts from CSVs. Defaults to latest `limit` accounts sorted by created_at desc."""
    svc = AccountService()
    results = svc.search_accounts(search=search, risk=risk, limit=limit, offset=offset)
    return results


@router.get("/{account_id}")
async def get_account(account_id: str):
    svc = AccountService()
    account = svc.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account
