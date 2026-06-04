"""Sync Control Router - Beauty & Shine ERP.

Handles:
- Sync queue management (POS → ERP)
- Device binding & branch cache
- Connectivity recovery detection
- Sync approval flow
- Integration logging
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.domain_models import SyncStatus, AuditAction
from pos_erp.repository import AuditTrailRepository
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

router = APIRouter(prefix="/api/sync", tags=["Sync & Integration"])

# ── Request Models ────────────────────────────────────────────────

class SyncQueueRequest(BaseModel):
    source: str
    target: str
    doc_key: Optional[str] = None
    payload: Optional[dict] = None

class SyncApprovalRequest(BaseModel):
    batch_id: str
    approver_id: str

class DeviceBindingRequest(BaseModel):
    device_id: str
    branch_code: str

class BranchCacheRequest(BaseModel):
    branch_code: str
    service_catalog_version: Optional[str] = None
    staff_schedule_version: Optional[str] = None
    price_matrix_version: Optional[str] = None
    branch_config_version: Optional[str] = None


# ── Sync Queue ────────────────────────────────────────────────────

@router.get("/queue")
def list_sync_queue(
    status: str = "",
    source: str = "",
    target: str = "",
    offset: int = 0,
    limit: int = 50,
):
    """List sync queue items."""
    conditions = []
    params = []
    if status:
        conditions.append("status = %s")
        params.append(status)
    if source:
        conditions.append("source = %s")
        params.append(source)
    if target:
        conditions.append("target = %s")
        params.append(target)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    
    rows = fetch_all(
        f"SELECT * FROM sync_queue {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        tuple(params)
    )
    return {"items": rows}

@router.post("/queue")
def enqueue_sync(req: SyncQueueRequest):
    """Add item to sync queue."""
    import json
    payload_json = json.dumps(req.payload) if req.payload else None
    
    return execute_returning(
        """INSERT INTO sync_queue (source, target, doc_key, payload, status)
           VALUES (%s, %s, %s, %s, 'pending') RETURNING *""",
        (req.source, req.target, req.doc_key, payload_json)
    )

@router.put("/queue/{id}/process")
def process_sync_item(id: str):
    """Mark sync item as processed."""
    item = fetch_one("SELECT * FROM sync_queue WHERE id = %s", (id,))
    if not item:
        raise HTTPException(404, "Sync item not found")
    
    execute(
        "UPDATE sync_queue SET status='success', processed_at=NOW() WHERE id=%s",
        (id,)
    )
    
    # Log integration
    execute(
        """INSERT INTO integration_log (source, target, doc_key, request_payload, response_payload, status)
           VALUES (%s, %s, %s, %s, %s, 'success')""",
        (item["source"], item["target"], item["doc_key"], item["payload"], '{"status":"processed"}')
    )
    
    return fetch_one("SELECT * FROM sync_queue WHERE id = %s", (id,))

@router.put("/queue/{id}/fail")
def fail_sync_item(id: str, error: str = ""):
    """Mark sync item as failed."""
    item = fetch_one("SELECT * FROM sync_queue WHERE id = %s", (id,))
    if not item:
        raise HTTPException(404, "Sync item not found")
    
    retry_count = item["retry_count"] + 1
    new_status = "retry" if retry_count < 3 else "failed"
    
    execute(
        "UPDATE sync_queue SET status=%s, retry_count=%s, last_error=%s WHERE id=%s",
        (new_status, retry_count, error, id)
    )
    
    return fetch_one("SELECT * FROM sync_queue WHERE id = %s", (id,))

@router.post("/queue/retry")
def retry_failed_items():
    """Retry all failed items with retry_count < 3."""
    count = execute(
        "UPDATE sync_queue SET status='pending' WHERE status='failed' AND retry_count < 3"
    )
    return {"retried": count}

@router.post("/queue/approve")
def approve_sync_batch(req: SyncApprovalRequest):
    """Approve a sync batch for processing."""
    items = fetch_all(
        "SELECT * FROM sync_queue WHERE status = 'pending' LIMIT 50"
    )
    
    for item in items:
        execute(
            "UPDATE sync_queue SET status='processing' WHERE id=%s",
            (item["id"],)
        )
    
    AuditTrailRepository.record(
        doc_key=req.batch_id,
        module="sync",
        action="approve",
        user_id=req.approver_id,
        new_value=f"Approved {len(items)} sync items",
    )
    
    return {"approved": len(items), "batch_id": req.batch_id}

@router.get("/queue/stats")
def get_sync_stats():
    """Get sync queue statistics."""
    stats = fetch_all(
        """SELECT status, count(*) as count FROM sync_queue GROUP BY status"""
    )
    total = sum(s["count"] for s in stats)
    return {
        "total": total,
        "by_status": {s["status"]: s["count"] for s in stats},
    }


# ── Device Binding ────────────────────────────────────────────────

@router.get("/devices")
def list_devices(branch_code: str = ""):
    """List POS device bindings."""
    if branch_code:
        return {"items": fetch_all("SELECT * FROM device_binding WHERE branch_code = %s", (branch_code,))}
    return {"items": fetch_all("SELECT * FROM device_binding")}

@router.post("/devices")
def bind_device(req: DeviceBindingRequest):
    """Bind a POS device to a branch."""
    existing = fetch_one(
        "SELECT * FROM device_binding WHERE device_id = %s",
        (req.device_id,)
    )
    if existing:
        execute(
            "UPDATE device_binding SET branch_code=%s, active=true WHERE device_id=%s",
            (req.branch_code, req.device_id)
        )
        return fetch_one("SELECT * FROM device_binding WHERE device_id = %s", (req.device_id,))
    
    return execute_returning(
        "INSERT INTO device_binding (device_id, branch_code, active) VALUES (%s, %s, true) RETURNING *",
        (req.device_id, req.branch_code)
    )

@router.delete("/devices/{device_id}")
def unbind_device(device_id: str):
    """Unbind a POS device."""
    execute("UPDATE device_binding SET active = false WHERE device_id = %s", (device_id,))
    return {"status": "unbound", "device_id": device_id}


# ── Branch Cache ──────────────────────────────────────────────────

@router.get("/branch-cache")
def list_branch_caches():
    """List branch cache versions."""
    return {"items": fetch_all("SELECT * FROM branch_cache")}

@router.post("/branch-cache")
def update_branch_cache(req: BranchCacheRequest):
    """Update branch cache versions."""
    existing = fetch_one("SELECT * FROM branch_cache WHERE branch_code = %s", (req.branch_code,))
    if existing:
        execute(
            """UPDATE branch_cache SET 
               service_catalog_version=COALESCE(%s, service_catalog_version),
               staff_schedule_version=COALESCE(%s, staff_schedule_version),
               price_matrix_version=COALESCE(%s, price_matrix_version),
               branch_config_version=COALESCE(%s, branch_config_version),
               updated_at=NOW()
               WHERE branch_code=%s""",
            (req.service_catalog_version, req.staff_schedule_version,
             req.price_matrix_version, req.branch_config_version, req.branch_code)
        )
    else:
        execute(
            """INSERT INTO branch_cache (branch_code, service_catalog_version, staff_schedule_version, price_matrix_version, branch_config_version)
               VALUES (%s, %s, %s, %s, %s)""",
            (req.branch_code, req.service_catalog_version, req.staff_schedule_version,
             req.price_matrix_version, req.branch_config_version)
        )
    
    return fetch_one("SELECT * FROM branch_cache WHERE branch_code = %s", (req.branch_code,))


# ── Integration Log ───────────────────────────────────────────────

@router.get("/integration-log")
def list_integration_logs(
    source: str = "",
    target: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 50,
):
    """List integration logs."""
    conditions = []
    params = []
    if source:
        conditions.append("source = %s")
        params.append(source)
    if target:
        conditions.append("target = %s")
        params.append(target)
    if status:
        conditions.append("status = %s")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    
    rows = fetch_all(
        f"SELECT * FROM integration_log {where} ORDER BY timestamp DESC LIMIT %s OFFSET %s",
        tuple(params)
    )
    return {"items": rows}


# ── Connectivity Status ───────────────────────────────────────────

@router.get("/connectivity")
def get_connectivity_status():
    """Get current connectivity status and pending sync count."""
    pending = fetch_one("SELECT count(*) as count FROM sync_queue WHERE status = 'pending'")
    failed = fetch_one("SELECT count(*) as count FROM sync_queue WHERE status = 'failed'")
    processing = fetch_one("SELECT count(*) as count FROM sync_queue WHERE status = 'processing'")
    
    return {
        "status": "online",
        "pending_count": pending["count"] if pending else 0,
        "failed_count": failed["count"] if failed else 0,
        "processing_count": processing["count"] if processing else 0,
    }
