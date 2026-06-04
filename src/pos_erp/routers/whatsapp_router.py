"""WhatsApp Booking Router — Beauty & Shine POS-ERP V6."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp Booking"])


class WebhookPayload(BaseModel):
    phone: str
    message: str
    message_type: str = "text"
    timestamp: Optional[str] = None
    metadata: Optional[dict] = None


class SessionUpdate(BaseModel):
    customer_id: Optional[str] = None
    status: Optional[str] = None


class ReplyPayload(BaseModel):
    message: str
    message_type: str = "text"


@router.get("/sessions")
def list_sessions(
    status: Optional[str] = None,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
):
    conditions, params = [], []
    if status:
        conditions.append("ws.status = %s")
        params.append(status)
    if search:
        conditions.append("(ws.phone ILIKE %s OR c.name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"""SELECT ws.*, c.name AS customer_name, c.phone AS customer_phone,
                (SELECT COUNT(*) FROM whatsapp_message wm WHERE wm.session_id = ws.id) AS message_count,
                (SELECT content FROM whatsapp_message wm WHERE wm.session_id = ws.id ORDER BY wm.created_at DESC LIMIT 1) AS last_message
            FROM whatsapp_session ws
            LEFT JOIN customer c ON ws.customer_id = c.id
            {where} ORDER BY ws.last_message_at DESC NULLS LAST LIMIT %s OFFSET %s""",
        tuple(params),
    )
    return {"sessions": rows, "total": len(rows)}


@router.get("/sessions/{session_id}")
def get_session(session_id: int):
    session = fetch_one(
        """SELECT ws.*, c.name AS customer_name FROM whatsapp_session ws
           LEFT JOIN customer c ON ws.customer_id = c.id WHERE ws.id = %s""",
        (session_id,),
    )
    if not session:
        raise HTTPException(404, "Session not found")
    messages = fetch_all(
        "SELECT * FROM whatsapp_message WHERE session_id = %s ORDER BY created_at DESC LIMIT 100",
        (session_id,),
    )
    return {**session, "messages": messages}


@router.post("/webhook")
def receive_webhook(data: WebhookPayload):
    """Receive incoming WhatsApp message — creates/finds session."""
    # Find or create session
    session = fetch_one(
        "SELECT * FROM whatsapp_session WHERE phone = %s AND status = 'active' ORDER BY last_message_at DESC LIMIT 1",
        (data.phone,),
    )
    if not session:
        # Try match customer by phone
        customer = fetch_one("SELECT id FROM customer WHERE phone = %s", (data.phone,))
        session = execute_returning(
            """INSERT INTO whatsapp_session (phone, customer_id, last_message_at)
               VALUES (%s, %s, now()) RETURNING *""",
            (data.phone, customer["id"] if customer else None),
        )
    else:
        execute("UPDATE whatsapp_session SET last_message_at = now() WHERE id = %s", (session["id"],))  # type: ignore[index]

    session_id = session["id"]  # type: ignore[index]

    # Save incoming message
    execute(
        """INSERT INTO whatsapp_message (session_id, direction, message_type, content, metadata)
           VALUES (%s, 'inbound', %s, %s, %s)""",
        (session_id, data.message_type, data.message, _json(data.metadata or {})),
    )

    # Parse booking intent from message
    intent = _parse_intent(data.message)
    return {"session_id": session_id, "intent": intent, "status": "received"}


@router.post("/sessions/{session_id}/reply")
def send_reply(session_id: int, data: ReplyPayload):
    """Send outbound reply to a WhatsApp session."""
    session = fetch_one("SELECT * FROM whatsapp_session WHERE id = %s", (session_id,))
    if not session:
        raise HTTPException(404, "Session not found")
    execute(
        """INSERT INTO whatsapp_message (session_id, direction, message_type, content)
           VALUES (%s, 'outbound', %s, %s)""",
        (session_id, data.message_type, data.message),
    )
    execute("UPDATE whatsapp_session SET last_message_at = now() WHERE id = %s", (session_id,))
    return {"sent": True, "session_id": session_id}


@router.post("/sessions/{session_id}/link-customer")
def link_customer(session_id: int, customer_id: str):
    """Link session to existing customer."""
    execute("UPDATE whatsapp_session SET customer_id = %s, updated_at = now() WHERE id = %s", (customer_id, session_id))
    return {"linked": True}


@router.post("/sessions/{session_id}/close")
def close_session(session_id: int):
    execute("UPDATE whatsapp_session SET status = 'closed', updated_at = now() WHERE id = %s", (session_id,))
    return {"closed": True}


@router.get("/stats")
def whatsapp_stats():
    total = fetch_one("SELECT COUNT(*) AS cnt FROM whatsapp_session")
    active = fetch_one("SELECT COUNT(*) AS cnt FROM whatsapp_session WHERE status = 'active'")
    today_msgs = fetch_one("SELECT COUNT(*) AS cnt FROM whatsapp_message WHERE created_at::date = CURRENT_DATE")
    pending_bookings = fetch_one(
        "SELECT COUNT(*) AS cnt FROM pos_transaction WHERE source = 'whatsapp' AND status = 'pending'"
    )
    return {
        "total_sessions": (total or {}).get("cnt", 0),
        "active_sessions": (active or {}).get("cnt", 0),
        "today_messages": (today_msgs or {}).get("cnt", 0),
        "pending_bookings": (pending_bookings or {}).get("cnt", 0),
    }


def _parse_intent(message: str) -> dict:
    """Simple keyword-based intent parsing for WhatsApp messages."""
    msg = message.lower().strip()
    if any(w in msg for w in ["booking", "pesan", "jadwal", "appointment", "reservasi"]):
        return {"type": "booking", "confidence": "high"}
    elif any(w in msg for w in ["harga", "price", "biaya", "tarif"]):
        return {"type": "price_inquiry", "confidence": "medium"}
    elif any(w in msg for w in ["promo", "diskon", "discount", "voucher"]):
        return {"type": "promo_inquiry", "confidence": "medium"}
    elif any(w in msg for w in ["cancel", "batal"]):
        return {"type": "cancellation", "confidence": "high"}
    elif any(w in msg for w in ["jam", "buka", "tutup", "lokasi", "alamat"]):
        return {"type": "info_inquiry", "confidence": "medium"}
    return {"type": "general", "confidence": "low"}


def _json(v):
    import json
    return json.dumps(v) if isinstance(v, dict) else v
