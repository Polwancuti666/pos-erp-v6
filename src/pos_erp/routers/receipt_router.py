"""Receipt Router - Beauty & Shine ERP.

Provides receipt data endpoints for thermal printer (58mm) output:
- GET /api/receipt/{transaction_id}       → JSON receipt data
- GET /api/receipt/{transaction_id}/html  → Print-optimized HTML receipt
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from pos_erp.db import fetch_one, fetch_all

router = APIRouter(prefix="/api/receipt", tags=["Receipt"])


def _fmt_currency(value) -> str:
    """Format number as IDR currency string."""
    if value is None:
        value = 0
    try:
        v = int(float(value))
    except (ValueError, TypeError):
        v = 0
    s = f"{v:,}".replace(",", ".")
    return f"Rp {s}"


def _dashed_line(width: int = 32) -> str:
    return "-" * width


def _center(text: str, width: int = 32) -> str:
    return text.center(width)


def _row(label: str, value: str, width: int = 32) -> str:
    """Right-align value, left-align label within width."""
    space = width - len(label) - len(value)
    if space < 1:
        space = 1
    return f"{label}{' ' * space}{value}"


def _build_receipt_data(transaction_id: str) -> dict:
    """Fetch and assemble complete receipt data from the database."""
    # ── Transaction (support both doc_key and UUID) ────────────────
    base_query = """SELECT t.*,
                  pm.name AS payment_method_name,
                  pm.type AS payment_method_type,
                  b.name  AS branch_name,
                  b.address AS branch_address,
                  b.phone AS branch_phone,
                  u.full_name AS cashier_name
           FROM pos_transaction t
           LEFT JOIN payment_method pm ON t.payment_method_id = pm.id
           LEFT JOIN branch b          ON t.branch_id = b.id
           LEFT JOIN app_user u        ON t.cashier_id = u.id"""
    txn = fetch_one(f"{base_query} WHERE t.doc_key = %s", (transaction_id,))
    if not txn:
        txn = fetch_one(f"{base_query} WHERE t.id = %s", (transaction_id,))
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn_uuid = txn["id"]

    # ── Items ──────────────────────────────────────────────────────
    items = fetch_all(
        """SELECT item_name, qty, unit_price, total, item_type
           FROM pos_transaction_item
           WHERE transaction_id = %s
           ORDER BY item_type, item_name""",
        (txn_uuid,),
    )

    # ── Therapist (first treatment_record linked to this transaction) ──
    therapist_name = "-"
    therapist_row = fetch_one(
        """SELECT u.full_name
           FROM treatment_record tr
           LEFT JOIN app_user u ON tr.therapist_id = u.id
           WHERE tr.transaction_id = %s
           ORDER BY tr.start_time NULLS LAST
           LIMIT 1""",
        (txn_uuid,),
    )
    if therapist_row and therapist_row.get("full_name"):
        therapist_name = therapist_row["full_name"]

    # ── Voucher (look for any linked voucher via the discount amount) ─
    voucher = None
    if txn.get("discount") and float(txn["discount"]) > 0:
        # Try to find a voucher applied to this transaction by looking at
        # the most recent audit trail entry mentioning a voucher.
        voucher_row = fetch_one(
            """SELECT new_value FROM audit_trail
               WHERE doc_key = %s AND new_value LIKE '%%Voucher applied%%'
               ORDER BY timestamp DESC LIMIT 1""",
            (txn.get("doc_key", ""),),
        )
        if voucher_row and voucher_row.get("new_value"):
            # Extract code from "Voucher applied: CODE"
            parts = str(voucher_row["new_value"]).split(":")
            code = parts[-1].strip() if len(parts) > 1 else ""
            if code:
                voucher = fetch_one(
                    "SELECT code, type, value FROM voucher WHERE code = %s",
                    (code,),
                )

    # ── Loyalty points earned (1 point per 10 000 IDR of total) ───
    loyalty_points = 0
    if txn.get("total"):
        loyalty_points = max(int(float(txn["total"]) / 10_000), 0)

    # ── Build response ─────────────────────────────────────────────
    return {
        "doc_key": txn.get("doc_key"),
        "customer_name": txn.get("customer_name") or "-",
        "customer_phone": txn.get("customer_phone") or "-",
        "status": txn.get("status"),
        "subtotal": float(txn.get("subtotal") or 0),
        "discount": float(txn.get("discount") or 0),
        "tax": float(txn.get("tax") or 0),
        "total": float(txn.get("total") or 0),
        "created_at": txn.get("created_at"),
        "payment_method": txn.get("payment_method_name") or txn.get("payment_method_type") or "-",
        "branch_name": txn.get("branch_name") or "-",
        "branch_address": txn.get("branch_address") or "-",
        "branch_phone": txn.get("branch_phone") or "-",
        "cashier_name": txn.get("cashier_name") or "-",
        "therapist_name": therapist_name,
        "voucher_code": voucher["code"] if voucher else None,
        "voucher_type": voucher["type"] if voucher else None,
        "voucher_value": float(voucher["value"]) if voucher else None,
        "loyalty_points_earned": loyalty_points,
        "items": [
            {
                "item_name": r.get("item_name"),
                "qty": float(r.get("qty") or 1),
                "unit_price": float(r.get("unit_price") or 0),
                "total": float(r.get("total") or 0),
                "item_type": r.get("item_type"),
            }
            for r in items
        ],
    }


# ── JSON endpoint ──────────────────────────────────────────────────

@router.get("/{transaction_id}")
def get_receipt(transaction_id: str):
    """Return complete receipt data as JSON."""
    return _build_receipt_data(transaction_id)


# ── HTML endpoint ──────────────────────────────────────────────────

@router.get("/{transaction_id}/html", response_class=HTMLResponse)
def get_receipt_html(transaction_id: str):
    """Return a print-optimized HTML receipt matching Beauty & Shine format."""
    data = _build_receipt_data(transaction_id)

    # ── Date formatting ────────────────────────────────────────────
    created = data["created_at"]
    if isinstance(created, datetime):
        created = created.strftime("%d/%m/%Y %H:%M")
    elif isinstance(created, str):
        try:
            created = datetime.fromisoformat(created).strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
    else:
        created = str(created)

    # ── Payment label ──────────────────────────────────────────────
    pay_label = f"{data['payment_method']} - {_fmt_currency(data['total'])}"

    # ── Status label ───────────────────────────────────────────────
    status_raw = (data.get("status") or "").lower()
    status_label = "paid" if status_raw in ("paid", "completed", "selesai") else status_raw

    # ── Build items HTML ───────────────────────────────────────────
    items_html = ""
    for item in data["items"]:
        name = item["item_name"] or "-"
        qty = int(item["qty"]) if item["qty"] == int(item["qty"]) else item["qty"]
        unit = _fmt_currency(item["unit_price"])
        total = _fmt_currency(item["total"])
        items_html += f'<div class="item-name">{name}</div>\n'
        items_html += f'<div class="row"><span>{qty} x {unit}</span><span>{total}</span></div>\n'

    # ── Build receipt HTML ─────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Struk {data['doc_key']}</title>
<style>
  @media print {{
    body {{ margin: 0; padding: 0; }}
    @page {{ size: 80mm auto; margin: 3mm; }}
  }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    color: #000;
    font-size: 14px;
    width: 300px;
    margin: 0 auto;
    padding: 10px;
    background: #fff;
    -webkit-print-color-adjust: exact;
  }}
  .header {{ text-align: center; margin-bottom: 10px; }}
  .title {{ font-size: 22px; font-weight: 700; margin-bottom: 2px; }}
  .subtitle {{ font-size: 13px; font-weight: 400; color: #333; }}
  .divider {{ border-top: 1px dashed #c0c0c0; margin: 10px 0; }}
  .row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    line-height: 22px;
  }}
  .row span:last-child {{ text-align: right; }}
  .row-bold span:last-child {{ font-weight: 700; }}
  .item-name {{ font-weight: 700; font-size: 15px; margin-top: 6px; margin-bottom: 2px; }}
  .item-price {{ font-size: 12px; color: #444; }}
  .total-row {{ font-weight: 700; font-size: 18px; line-height: 26px; }}
  .footer {{
    text-align: center;
    font-size: 12px;
    color: #444;
    margin-top: 14px;
  }}
</style>
</head>
<body>
<div class="header">
  <div class="title">{data['branch_name']}</div>
  <div class="subtitle">Struk Transaksi</div>
</div>
<div class="divider"></div>
<div class="row row-bold"><span>No. Transaksi</span><span>{data['doc_key']}</span></div>
<div class="row"><span>Tanggal</span><span>{created}</span></div>
<div class="row"><span>Customer</span><span>{data['customer_name']}</span></div>
<div class="row"><span>Therapist</span><span>{data['therapist_name']}</span></div>
<div class="divider"></div>
{items_html}<div class="divider"></div>
<div class="row"><span>Subtotal</span><span>{_fmt_currency(data['subtotal'])}</span></div>
<div class="row"><span>Diskon</span><span>{_fmt_currency(data['discount'])}</span></div>
<div class="row"><span>Pajak</span><span>{_fmt_currency(data['tax'])}</span></div>
<div class="divider"></div>
<div class="row total-row"><span>Total</span><span>{_fmt_currency(data['total'])}</span></div>
<div class="row"><span>Pembayaran</span><span>{pay_label}</span></div>
<div class="row"><span>Status</span><span>{status_label}</span></div>
<div class="footer">Terima kasih atas kunjungan Anda.</div>
<script>window.onload = function() {{ window.print(); }};</script>
</body>
</html>"""
    return HTMLResponse(content=html)
