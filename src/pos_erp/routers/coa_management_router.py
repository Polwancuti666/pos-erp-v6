"""COA Management Router — Post-onboarding accounts, edit, mapping review.
Works alongside coa_upload_router which handles upload/validate/apply."""

from __future__ import annotations
import re
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/coa", tags=["COA Management"])

VALID_ACCOUNT_TYPES = {"ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"}


# ── Pydantic Models ────────────────────────────────────────────────

class AddAccountRequest(BaseModel):
    parent_code: str
    account_code: str
    account_name: str
    is_active: bool = True


class EditNameRequest(BaseModel):
    account_name: str


class EditCodeRequest(BaseModel):
    account_code: str


class EditStatusRequest(BaseModel):
    is_active: bool


class MappingOverrideRequest(BaseModel):
    account_code: str


# ── ACCOUNTS CRUD (Post-Onboarding) ────────────────────────────────

@router.get("/accounts")
def list_accounts(
    level: Optional[int] = None,
    parent_code: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    offset: int = 0,
    limit: int = 200,
):
    """List COA accounts with filters."""
    conditions, params = [], []
    if level is not None:
        conditions.append("level = %s")
        params.append(level)
    if parent_code:
        conditions.append("parent_code = %s")
        params.append(parent_code)
    if search:
        conditions.append("(account_code ILIKE %s OR account_name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(is_active)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"SELECT * FROM chart_of_account {where} ORDER BY account_code LIMIT %s OFFSET %s",
        tuple(params),
    )
    return {"accounts": rows, "total": len(rows)}


@router.get("/accounts/{account_id}")
def get_account(account_id: str):
    """Get single account."""
    row = fetch_one("SELECT * FROM chart_of_account WHERE id = %s", (account_id,))
    if not row:
        raise HTTPException(404, "Account not found")
    return row


@router.get("/accounts/{account_id}/usage-count")
def get_usage_count(account_id: str):
    """Get usage count for an account."""
    row = fetch_one("SELECT usage_count, last_used_at FROM chart_of_account WHERE id = %s", (account_id,))
    if not row:
        raise HTTPException(404, "Account not found")
    return {"count": row["usage_count"] or 0, "last_used": row["last_used_at"]}


@router.post("/accounts/suggest-code")
def suggest_code(parent_code: str):
    """Suggest next account code based on parent."""
    children = fetch_all(
        "SELECT account_code FROM chart_of_account WHERE parent_code = %s ORDER BY account_code DESC",
        (parent_code,),
    )
    if not children:
        return {"suggested_code": f"{parent_code}.1"}
    last = children[0]["account_code"]
    parts = last.split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
        return {"suggested_code": ".".join(parts)}
    except ValueError:
        return {"suggested_code": f"{parent_code}.1"}


@router.get("/accounts/check-code/{code}")
def check_code(code: str):
    """Check if account code is available."""
    existing = fetch_one("SELECT id FROM chart_of_account WHERE account_code = %s", (code,))
    return {"available": existing is None}


@router.get("/accounts/check-name/{name}")
def check_name(name: str):
    """Check if account name already exists."""
    existing = fetch_one(
        "SELECT account_code, account_name FROM chart_of_account WHERE LOWER(account_name) = LOWER(%s)",
        (name,),
    )
    return {
        "exists": existing is not None,
        "existing_code": existing["account_code"] if existing else None,
    }


@router.get("/accounts/suggest-match")
def suggest_match(item_name: str):
    """Suggest COA account match for a POS item name."""
    accounts = fetch_all(
        "SELECT id, account_code, account_name FROM chart_of_account WHERE level = 4 AND is_active = true"
    )
    best = None
    best_score = 0
    for acc in accounts:
        aname = (acc["account_name"] or "").lower()
        iname = item_name.lower()
        if aname == iname:
            score = 100
        elif aname in iname or iname in aname:
            score = 80
        else:
            common = len(set(aname.split()) & set(iname.split()))
            total = max(len(set(aname.split()) | set(iname.split())), 1)
            score = int((common / total) * 70)
        if score > best_score:
            best_score = score
            best = acc

    return {
        "suggested_account": best,
        "confidence": best_score,
        "diff_highlight": f"POS: '{item_name}' vs COA: '{best['account_name']}'" if best else None,
    }


@router.post("/accounts")
def add_account(req: AddAccountRequest):
    """Add new COA account post-onboarding."""
    parent = fetch_one(
        "SELECT level, account_type FROM chart_of_account WHERE account_code = %s",
        (req.parent_code,),
    )
    if not parent:
        raise HTTPException(404, f"Parent account '{req.parent_code}' not found")

    new_level = parent["level"] + 1
    if new_level > 4:
        raise HTTPException(400, "Cannot add beyond Level 4")

    existing = fetch_one("SELECT id FROM chart_of_account WHERE account_code = %s", (req.account_code,))
    if existing:
        raise HTTPException(409, f"Account code '{req.account_code}' already exists")

    name_exists = fetch_one(
        "SELECT account_code FROM chart_of_account WHERE LOWER(account_name) = LOWER(%s)",
        (req.account_name,),
    )

    row = execute_returning(
        """INSERT INTO chart_of_account (account_code, account_name, account_type, parent_code, level, is_active, created_from)
           VALUES (%s, %s, %s, %s, %s, %s, 'manual') RETURNING *""",
        (req.account_code, req.account_name, parent["account_type"],
         req.parent_code, new_level, req.is_active),
    )

    match_result = None
    if new_level == 4:
        treatments = fetch_all("SELECT id, name FROM treatment WHERE is_active = true")
        for t in treatments:
            tname = (t["name"] or "").lower()
            aname = req.account_name.lower()
            if tname in aname or aname in tname:
                execute(
                    "INSERT INTO coa_mapping (coa_id, mapping_type, item_type, item_id, item_name, confidence) VALUES (%s, %s, 'treatment', %s, %s, 80)",
                    (row["id"], f"service:{t['id']}", t["id"], t["name"]),
                )
                execute("UPDATE chart_of_account SET mapping_status = 'mapped', mapped_to_type = %s, mapping_confidence = 80 WHERE id = %s",
                        (f"service:{t['id']}", row["id"]))
                match_result = {"matched": True, "item": t["name"]}
                break

    return {
        **row,
        "name_warning": name_exists is not None,
        "match_result": match_result,
    }


# ── EDIT ACCOUNT (with safeguards) ─────────────────────────────────

@router.put("/accounts/{account_id}/name")
def edit_account_name(account_id: str, req: EditNameRequest):
    """Edit account name — always allowed."""
    existing = fetch_one("SELECT * FROM chart_of_account WHERE id = %s", (account_id,))
    if not existing:
        raise HTTPException(404, "Account not found")

    old_name = existing["account_name"]
    execute("UPDATE chart_of_account SET account_name = %s WHERE id = %s", (req.account_name, account_id))

    execute(
        "INSERT INTO coa_audit_log (coa_id, action, field_changed, old_value, new_value) VALUES (%s, 'edit', 'account_name', %s, %s)",
        (account_id, old_name, req.account_name),
    )

    return {
        "updated": True,
        "warning": "Perubahan nama akun bisa mempengaruhi mapping transaksi baru. Transaksi yang sudah ada tidak terpengaruh.",
    }


@router.put("/accounts/{account_id}/code")
def edit_account_code(account_id: str, req: EditCodeRequest):
    """Edit account code — only if not used in transactions."""
    existing = fetch_one("SELECT * FROM chart_of_account WHERE id = %s", (account_id,))
    if not existing:
        raise HTTPException(404, "Account not found")

    usage = existing["usage_count"] or 0
    if usage > 0:
        raise HTTPException(
            403,
            f"Kode akun tidak bisa diubah. Akun ini sudah digunakan di {usage} transaksi. "
            "Nonaktifkan akun ini dan buat akun baru dengan kode yang benar.",
        )

    dup = fetch_one("SELECT id FROM chart_of_account WHERE account_code = %s AND id != %s", (req.account_code, account_id))
    if dup:
        raise HTTPException(409, f"Kode '{req.account_code}' sudah digunakan")

    old_code = existing["account_code"]
    execute("UPDATE chart_of_account SET account_code = %s WHERE id = %s", (req.account_code, account_id))

    execute(
        "INSERT INTO coa_audit_log (coa_id, action, field_changed, old_value, new_value) VALUES (%s, 'edit', 'account_code', %s, %s)",
        (account_id, old_code, req.account_code),
    )

    return {"updated": True}


@router.put("/accounts/{account_id}/status")
def edit_account_status(account_id: str, req: EditStatusRequest):
    """Toggle account active status."""
    existing = fetch_one("SELECT * FROM chart_of_account WHERE id = %s", (account_id,))
    if not existing:
        raise HTTPException(404, "Account not found")

    usage = existing["usage_count"] or 0
    warning = None
    if not req.is_active and usage > 0:
        warning = f"Ada {usage} transaksi yang menggunakan akun ini. Transaksi yang sudah ada tetap valid. Transaksi baru tidak bisa menggunakan akun ini setelah dinonaktifkan."

    execute("UPDATE chart_of_account SET is_active = %s WHERE id = %s", (req.is_active, account_id))

    execute(
        "INSERT INTO coa_audit_log (coa_id, action, field_changed, old_value, new_value) VALUES (%s, 'status_change', 'is_active', %s, %s)",
        (account_id, str(existing["is_active"]), str(req.is_active)),
    )

    return {"updated": True, "warning": warning}


# ── MAPPING REVIEW ─────────────────────────────────────────────────

@router.get("/mapping-review")
def mapping_review():
    """Get mapping review data (3 tabs)."""
    auto = fetch_all(
        """SELECT cm.id, cm.coa_id, cm.mapping_type, cm.item_type, cm.confidence,
                  coa.account_code, coa.account_name
           FROM coa_mapping cm
           JOIN chart_of_account coa ON cm.coa_id = coa.id
           WHERE cm.is_confirmed = true OR cm.confidence >= 80
           ORDER BY cm.confidence DESC"""
    )
    needs = fetch_all(
        """SELECT cm.id, cm.coa_id, cm.mapping_type, cm.item_type, cm.confidence,
                  coa.account_code, coa.account_name
           FROM coa_mapping cm
           JOIN chart_of_account coa ON cm.coa_id = coa.id
           WHERE cm.is_confirmed = false AND cm.confidence < 80
           ORDER BY cm.confidence"""
    )
    not_found = fetch_all(
        """SELECT id, account_code, account_name, account_type
           FROM chart_of_account
           WHERE mapping_status = 'unmapped' AND level = 4 AND is_active = true"""
    )
    return {"auto_mapped": auto, "needs_review": needs, "not_found": not_found}


@router.put("/mapping-review/{mapping_id}")
def override_mapping(mapping_id: int, req: MappingOverrideRequest):
    """Override mapping for an item."""
    coa = fetch_one("SELECT id FROM chart_of_account WHERE account_code = %s", (req.account_code,))
    if not coa:
        raise HTTPException(404, "Account not found")
    execute(
        "UPDATE coa_mapping SET coa_id = %s, is_confirmed = true, confirmed_at = now(), confidence = 100 WHERE id = %s",
        (coa["id"], mapping_id),
    )
    return {"updated": True}


@router.post("/mapping-review/confirm-all-auto")
def confirm_all_auto():
    """Confirm all auto-mapped items."""
    n = execute(
        "UPDATE coa_mapping SET is_confirmed = true, confirmed_at = now() WHERE confidence >= 80 AND is_confirmed = false"
    )
    return {"confirmed": n}


@router.post("/mapping-review/go-live")
def go_live():
    """Go-live — check if all reviews are resolved."""
    pending = fetch_one(
        "SELECT COUNT(*) AS cnt FROM coa_mapping WHERE is_confirmed = false AND confidence < 80"
    )
    pending_count = (pending or {}).get("cnt", 0)
    return {
        "success": pending_count == 0,
        "pending_items": pending_count,
    }


# ── RETRY POSTING ──────────────────────────────────────────────────

@router.post("/retry-posting")
def retry_posting(exception_id: int):
    """Retry posting after COA fix."""
    return {"status": "retry_initiated", "exception_id": exception_id}


# ── AUDIT LOG ──────────────────────────────────────────────────────

@router.get("/audit-log")
def audit_log(coa_id: Optional[str] = None, limit: int = 50):
    """Get COA audit log."""
    conditions, params = [], []
    if coa_id:
        conditions.append("cal.coa_id = %s")
        params.append(coa_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)
    rows = fetch_all(
        f"""SELECT cal.*, coa.account_code, coa.account_name
            FROM coa_audit_log cal
            LEFT JOIN chart_of_account coa ON cal.coa_id = coa.id
            {where} ORDER BY cal.changed_at DESC LIMIT %s""",
        tuple(params),
    )
    return {"logs": rows}
