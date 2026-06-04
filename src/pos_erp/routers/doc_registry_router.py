"""Document Number Registry Router - Beauty & Shine ERP.

BPMN 2.0 v3: Centralized document key generation + cross-reference store.
Format: MODULE-BRANCH-YYYYMMDD-SEQUENCE
Example: BOOK-BSD-20260518-0001, POS-BSD-20260518-0001
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/doc-registry", tags=["Document Registry"])

# Module codes per BPMN 2.0 v3
MODULE_CODES = {
    "BOOK": "Booking",
    "POS": "POS Transaction",
    "TRM": "Treatment Record",
    "STK": "Stock Movement",
    "WIP": "WIP/Manufacture",
    "AP": "Accounts Payable",
    "BP": "Bank Payment",
    "JE": "Journal Entry",
    "FA": "Fixed Asset",
    "EOP": "End of Period",
    "INV": "Inventory Opname",
    "BOM": "Bill of Material",
    "ADJ": "Adjustment/Reversal",
}


# ── Document Key Generator ───────────────────────────────────────

class GenerateDocKeyRequest(BaseModel):
    module_code: str
    branch_code: str = "HQ"

class GenerateDocKeyResponse(BaseModel):
    doc_key: str
    module_code: str
    branch_code: str
    year_month: str
    sequence: int

@router.post("/generate", response_model=GenerateDocKeyResponse)
def generate_doc_key(req: GenerateDocKeyRequest):
    """Generate a unique document key: MODULE-BRANCH-YYYYMMDD-SEQUENCE."""
    module_code = req.module_code.upper()
    branch_code = req.branch_code.upper()
    
    if module_code not in MODULE_CODES:
        raise HTTPException(status_code=400, detail=f"Unknown module code: {module_code}. Valid: {list(MODULE_CODES.keys())}")
    
    today = date.today()
    year_month = today.strftime("%Y%m")
    date_str = today.strftime("%Y%m%d")
    
    # Upsert sequence counter (atomic increment)
    existing = fetch_one(
        "SELECT * FROM doc_number_sequence WHERE module_code=%s AND branch_code=%s AND year_month=%s",
        (module_code, branch_code, year_month)
    )
    
    if existing:
        new_seq = existing["current_seq"] + 1
        execute(
            "UPDATE doc_number_sequence SET current_seq=%s, updated_at=NOW() WHERE id=%s",
            (new_seq, existing["id"])
        )
    else:
        new_seq = 1
        execute(
            "INSERT INTO doc_number_sequence (module_code, branch_code, year_month, current_seq) VALUES (%s,%s,%s,%s)",
            (module_code, branch_code, year_month, new_seq)
        )
    
    doc_key = f"{module_code}-{branch_code}-{date_str}-{new_seq:04d}"
    
    return GenerateDocKeyResponse(
        doc_key=doc_key,
        module_code=module_code,
        branch_code=branch_code,
        year_month=year_month,
        sequence=new_seq,
    )


# ── Cross-Reference Management ───────────────────────────────────

class LinkDocsRequest(BaseModel):
    source_doc_key: str
    source_module: str
    target_doc_key: str
    target_module: str
    relationship: str = "linked"

@router.post("/link")
def link_documents(req: LinkDocsRequest):
    """Create a cross-reference link between two documents."""
    execute(
        """INSERT INTO doc_cross_reference (source_doc_key, source_module, target_doc_key, target_module, relationship)
           VALUES (%s,%s,%s,%s,%s)""",
        (req.source_doc_key, req.source_module.upper(), req.target_doc_key, req.target_module.upper(), req.relationship)
    )
    return {"message": "Documents linked", "source": req.source_doc_key, "target": req.target_doc_key}

@router.get("/links/{doc_key}")
def get_document_links(doc_key: str):
    """Get all cross-reference links for a document key."""
    outbound = fetch_all(
        "SELECT * FROM doc_cross_reference WHERE source_doc_key=%s ORDER BY created_at DESC",
        (doc_key,)
    )
    inbound = fetch_all(
        "SELECT * FROM doc_cross_reference WHERE target_doc_key=%s ORDER BY created_at DESC",
        (doc_key,)
    )
    return {
        "doc_key": doc_key,
        "outbound_links": outbound,
        "inbound_links": inbound,
        "total_links": len(outbound) + len(inbound),
    }


# ── Registry Browser ─────────────────────────────────────────────

@router.get("/sequences")
def list_sequences(module_code: str = "", branch_code: str = ""):
    """List document number sequences with optional filters."""
    conditions = []
    params = []
    if module_code:
        conditions.append("module_code = %s")
        params.append(module_code.upper())
    if branch_code:
        conditions.append("branch_code = %s")
        params.append(branch_code.upper())
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    rows = fetch_all(
        f"SELECT * FROM doc_number_sequence {where} ORDER BY module_code, branch_code, year_month DESC LIMIT 200",
        tuple(params)
    )
    return {"items": rows}

@router.get("/modules")
def list_module_codes():
    """List all valid module codes."""
    return {"modules": MODULE_CODES}

@router.get("/search")
def search_documents(q: str = "", module: str = "", limit: int = 50):
    """Search across all document keys in the system."""
    conditions = []
    params = []
    if q:
        conditions.append("(source_doc_key ILIKE %s OR target_doc_key ILIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    if module:
        conditions.append("(source_module = %s OR target_module = %s)")
        params.extend([module.upper(), module.upper()])
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)
    
    rows = fetch_all(
        f"""SELECT DISTINCT ON (doc_key) doc_key, module, created_at FROM (
                SELECT source_doc_key as doc_key, source_module as module, created_at FROM doc_cross_reference {where}
                UNION
                SELECT target_doc_key as doc_key, target_module as module, created_at FROM doc_cross_reference {where}
            ) combined ORDER BY doc_key, created_at DESC LIMIT %s""",
        tuple(params)
    )
    return {"items": rows}

@router.get("/stats")
def get_registry_stats():
    """Get document registry statistics."""
    total_sequences = fetch_one("SELECT COUNT(*) as cnt FROM doc_number_sequence")
    total_xrefs = fetch_one("SELECT COUNT(*) as cnt FROM doc_cross_reference")
    
    by_module = fetch_all(
        """SELECT module_code, branch_code, SUM(current_seq) as total_docs
           FROM doc_number_sequence GROUP BY module_code, branch_code ORDER BY module_code"""
    )
    
    xref_by_module = fetch_all(
        """SELECT source_module, COUNT(*) as links
           FROM doc_cross_reference GROUP BY source_module ORDER BY links DESC"""
    )
    
    return {
        "total_sequences": total_sequences["cnt"] if total_sequences else 0,
        "total_cross_references": total_xrefs["cnt"] if total_xrefs else 0,
        "sequences_by_module": by_module,
        "links_by_module": xref_by_module,
    }


# ── Integration Log ──────────────────────────────────────────────

@router.get("/integration-log")
def list_integration_logs(doc_key: str = "", status: str = "", limit: int = 50):
    """List integration log entries."""
    conditions = []
    params = []
    if doc_key:
        conditions.append("doc_key = %s")
        params.append(doc_key)
    if status:
        conditions.append("status = %s")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)
    
    rows = fetch_all(
        f"SELECT * FROM integration_log {where} ORDER BY created_at DESC LIMIT %s",
        tuple(params)
    )
    return {"items": rows}
