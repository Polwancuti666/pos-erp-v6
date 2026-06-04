from __future__ import annotations
import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pos_erp.auth import create_access_token
from pos_erp.db import fetch_one, fetch_all, execute, execute_returning

router = APIRouter()


def _get_staff_from_db(staff_id: str) -> dict | None:
    """Look up staff from app_user table by username."""
    return fetch_one(
        "SELECT * FROM app_user WHERE username = %s AND is_active = true",
        (staff_id,),
    )


def _get_branch_id(branch_code: str) -> str | None:
    """Resolve branch code to UUID."""
    row = fetch_one("SELECT id FROM branch WHERE code = %s", (branch_code,))
    return str(row["id"]) if row else None


def _gen_shift_code(staff_id: str) -> str:
    now = datetime.datetime.now()
    return f"SFT-{staff_id}-{now.strftime('%Y%m%d%H%M%S')}"


# ── POST /pos/auth — Login ─────────────────────────────────────────
@router.post("/pos/auth")
async def pos_auth(request: Request):
    """Authenticate staff from app_user table. Does NOT open shift."""
    try:
        data = await request.json()
        staff_id = (data.get("staff_id") or "").strip().upper()
        pin = (data.get("pin") or "").strip()

        if not staff_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Staff ID wajib diisi"},
            )

        # Look up staff from database
        staff = _get_staff_from_db(staff_id)

        if not staff:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": f"Staff ID '{staff_id}' tidak ditemukan"},
            )

        # Verify PIN
        db_pin = staff.get("pin") or "1234"  # Default PIN if not set
        if pin != db_pin:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "PIN salah"},
            )

        # Get branch info
        branch_code = None
        if staff.get("branch_id"):
            branch = fetch_one("SELECT code FROM branch WHERE id = %s", (staff["branch_id"],))
            if branch:
                branch_code = branch["code"]

        # Get role from user_role table or pos_role column
        role = staff.get("pos_role") or "cashier"
        user_role = fetch_one(
            "SELECT role_name FROM user_role WHERE user_id = %s AND is_active = true",
            (staff["id"],),
        )
        if user_role:
            role = user_role["role_name"]

        # Check if staff already has an open shift
        existing = fetch_one(
            "SELECT * FROM pos_cashier_shift WHERE staff_id = %s AND status = 'open' ORDER BY opened_at DESC LIMIT 1",
            (staff_id,),
        )

        access_token = create_access_token(staff_id, role)

        result = {
            "success": True,
            "message": f"Selamat datang, {staff['full_name']}!",
            "staff": {
                "id": staff_id,
                "name": staff["full_name"],
                "role": role,
                "branch": branch_code or "HQ",
                "branch_id": str(staff["branch_id"]) if staff.get("branch_id") else None,
            },
            "access_token": access_token,
            "token_type": "bearer",
            "has_open_shift": existing is not None,
        }

        if existing:
            result["shift_id"] = str(existing["id"])
            result["shift_code"] = existing["shift_code"]
            result["opening_cash"] = float(existing["opening_cash"])

        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)},
        )


# ── POST /pos/shift/open — Open Shift ─────────────────────────────
@router.post("/pos/shift/open")
async def open_shift(request: Request):
    """Open a new cashier shift with opening cash amount."""
    try:
        data = await request.json()
        staff_id = (data.get("staff_id") or "").strip().upper()
        staff_name = data.get("staff_name", "")
        branch_code = data.get("branch_code", "HQ")
        branch_id_raw = data.get("branch_id")  # Accept direct UUID from frontend
        opening_cash = float(data.get("opening_cash", 0))

        if not staff_id:
            return JSONResponse(status_code=400, content={"success": False, "message": "Staff ID wajib"})

        if opening_cash < 0:
            return JSONResponse(status_code=400, content={"success": False, "message": "Kas awal tidak boleh negatif"})

        # Check if already has open shift
        existing = fetch_one(
            "SELECT id, shift_code FROM pos_cashier_shift WHERE staff_id = %s AND status = 'open'",
            (staff_id,),
        )
        if existing:
            return JSONResponse(
                status_code=409,
                content={"success": False, "message": f"Shift masih terbuka: {existing['shift_code']}", "shift_code": existing["shift_code"]},
            )

        branch_id = branch_id_raw if branch_id_raw else _get_branch_id(branch_code)
        shift_code = _gen_shift_code(staff_id)

        row = execute_returning(
            """INSERT INTO pos_cashier_shift
               (shift_code, staff_id, staff_name, branch_id, opening_cash, status, opened_at)
               VALUES (%s, %s, %s, %s, %s, 'open', NOW())
               RETURNING *""",
            (shift_code, staff_id, staff_name, branch_id, opening_cash),
        )

        return {
            "success": True,
            "message": f"Shift dibuka dengan kas awal Rp {opening_cash:,.0f}",
            "shift_id": str(row["id"]),
            "shift_code": shift_code,
            "opening_cash": opening_cash,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ── GET /pos/shift/current — Get Current Open Shift ───────────────
@router.get("/pos/shift/current")
async def get_current_shift(staff_id: str = ""):
    """Get current open shift for a staff member."""
    if not staff_id:
        return {"success": False, "message": "staff_id required"}

    shift = fetch_one(
        "SELECT * FROM pos_cashier_shift WHERE staff_id = %s AND status = 'open' ORDER BY opened_at DESC LIMIT 1",
        (staff_id,),
    )
    if not shift:
        return {"success": False, "has_shift": False}

    # Get transaction summary for this shift
    txn_summary = fetch_one(
        """SELECT
             COUNT(*) as txn_count,
             COALESCE(SUM(total), 0) as total_sales,
             COALESCE(SUM(CASE WHEN pm.type = 'cash' THEN total ELSE 0 END), 0) as cash_sales,
             COALESCE(SUM(CASE WHEN pm.type = 'qris' THEN total ELSE 0 END), 0) as qris_sales,
             COALESCE(SUM(CASE WHEN pm.type IN ('bank_transfer','e_wallet','card') THEN total ELSE 0 END), 0) as transfer_sales
           FROM pos_transaction pt
           LEFT JOIN payment_method pm ON pt.payment_method_id = pm.id
           WHERE pt.shift_id = %s AND pt.status = 'paid'""",
        (shift["id"],),
    )

    # Get treatment sales for this shift
    treatment_summary = fetch_one(
        """SELECT
             COUNT(*) as treatment_count,
             COALESCE(SUM(t.price), 0) as treatment_sales
           FROM treatment_record tr
           JOIN treatment t ON tr.treatment_id = t.id
           JOIN pos_transaction pt ON tr.transaction_id = pt.id
           WHERE pt.shift_id = %s AND pt.status = 'paid'""",
        (shift["id"],),
    )

    return {
        "success": True,
        "has_shift": True,
        "shift_id": str(shift["id"]),
        "shift_code": shift["shift_code"],
        "staff_id": shift["staff_id"],
        "staff_name": shift["staff_name"],
        "branch_id": str(shift["branch_id"]) if shift["branch_id"] else None,
        "opening_cash": float(shift["opening_cash"]),
        "opened_at": shift["opened_at"].isoformat() if shift["opened_at"] else None,
        "txn_count": txn_summary["txn_count"] if txn_summary else 0,
        "total_sales": float(txn_summary["total_sales"]) if txn_summary else 0,
        "cash_sales": float(txn_summary["cash_sales"]) if txn_summary else 0,
        "qris_sales": float(txn_summary["qris_sales"]) if txn_summary else 0,
        "transfer_sales": float(txn_summary["transfer_sales"]) if txn_summary else 0,
        "treatment_count": treatment_summary["treatment_count"] if treatment_summary else 0,
        "treatment_sales": float(treatment_summary["treatment_sales"]) if treatment_summary else 0,
    }


# ── POST /pos/shift/close — Close Shift ───────────────────────────
@router.post("/pos/shift/close")
async def close_shift(request: Request):
    """Close the current shift with closing cash amount."""
    try:
        data = await request.json()
        shift_id = data.get("shift_id", "")
        closing_cash = float(data.get("closing_cash", 0))
        notes = data.get("notes", "")

        if not shift_id:
            return JSONResponse(status_code=400, content={"success": False, "message": "shift_id wajib"})

        shift = fetch_one(
            "SELECT * FROM pos_cashier_shift WHERE id = %s AND status = 'open'",
            (shift_id,),
        )
        if not shift:
            return JSONResponse(status_code=404, content={"success": False, "message": "Shift tidak ditemukan atau sudah ditutup"})

        # Calculate totals
        txn_summary = fetch_one(
            """SELECT
                 COUNT(*) as txn_count,
                 COALESCE(SUM(total), 0) as total_sales,
                 COALESCE(SUM(CASE WHEN pm.type = 'cash' THEN total ELSE 0 END), 0) as cash_sales,
                 COALESCE(SUM(CASE WHEN pm.type = 'qris' THEN total ELSE 0 END), 0) as qris_sales,
                 COALESCE(SUM(CASE WHEN pm.type IN ('bank_transfer','e_wallet','card') THEN total ELSE 0 END), 0) as transfer_sales
               FROM pos_transaction pt
               LEFT JOIN payment_method pm ON pt.payment_method_id = pm.id
               WHERE pt.shift_id = %s AND pt.status = 'paid'""",
            (shift_id,),
        )

        treatment_summary = fetch_one(
            """SELECT
                 COUNT(*) as treatment_count,
                 COALESCE(SUM(t.price), 0) as treatment_sales
               FROM treatment_record tr
               JOIN treatment t ON tr.treatment_id = t.id
               JOIN pos_transaction pt ON tr.transaction_id = pt.id
               WHERE pt.shift_id = %s AND pt.status = 'paid'""",
            (shift_id,),
        )

        total_sales = float(txn_summary["total_sales"]) if txn_summary else 0
        cash_sales = float(txn_summary["cash_sales"]) if txn_summary else 0
        qris_sales = float(txn_summary["qris_sales"]) if txn_summary else 0
        transfer_sales = float(txn_summary["transfer_sales"]) if txn_summary else 0
        treatment_sales = float(treatment_summary["treatment_sales"]) if treatment_summary else 0
        txn_count = txn_summary["txn_count"] if txn_summary else 0

        # Expected cash = opening cash + cash sales
        expected_cash = float(shift["opening_cash"]) + cash_sales
        variance = closing_cash - expected_cash

        # Update shift
        execute_returning(
            """UPDATE pos_cashier_shift SET
                 closing_cash = %s,
                 expected_cash = %s,
                 total_sales = %s,
                 total_cash_sales = %s,
                 total_qris_sales = %s,
                 total_transfer_sales = %s,
                 total_treatment_sales = %s,
                 transaction_count = %s,
                 variance = %s,
                 status = 'closed',
                 closed_at = NOW(),
                 notes = %s,
                 updated_at = NOW()
               WHERE id = %s RETURNING *""",
            (closing_cash, expected_cash, total_sales, cash_sales, qris_sales,
             transfer_sales, treatment_sales, txn_count, variance, notes, shift_id),
        )

        status_msg = "Sesuai ✅" if abs(variance) < 1000 else ("Lebih +" if variance > 0 else "Kurang ")

        return {
            "success": True,
            "message": f"Shift ditutup. Variance: {status_msg} Rp {abs(variance):,.0f}",
            "shift_code": shift["shift_code"],
            "summary": {
                "opening_cash": float(shift["opening_cash"]),
                "closing_cash": closing_cash,
                "expected_cash": expected_cash,
                "total_sales": total_sales,
                "cash_sales": cash_sales,
                "qris_sales": qris_sales,
                "transfer_sales": transfer_sales,
                "treatment_sales": treatment_sales,
                "treatment_count": treatment_summary["treatment_count"] if treatment_summary else 0,
                "transaction_count": txn_count,
                "variance": variance,
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ── GET /pos/shift/history — Shift History ─────────────────────────
@router.get("/pos/shift/history")
async def shift_history(branch_id: str = "", limit: int = 20):
    """List recent shifts."""
    where = "WHERE 1=1"
    params: list = []
    if branch_id:
        where += " AND s.branch_id = %s"
        params.append(branch_id)
    params.append(limit)

    rows = fetch_all(
        f"""SELECT s.*, b.code as branch_code, b.name as branch_name
            FROM pos_cashier_shift s
            LEFT JOIN branch b ON s.branch_id = b.id
            {where}
            ORDER BY s.opened_at DESC
            LIMIT %s""",
        tuple(params),
    )
    return {"items": rows}


# ── POST /pos/end-shift (legacy compat) ────────────────────────────
@router.post("/pos/end-shift")
async def pos_end_shift(request: Request):
    """Legacy end-shift — now redirects to close-shift flow."""
    try:
        data = await request.json()
        shift_id = data.get("shift_id", "")
        if not shift_id:
            return JSONResponse(status_code=400, content={"success": False, "message": "shift_id required"})

        shift = fetch_one(
            "SELECT * FROM pos_cashier_shift WHERE id = %s AND status = 'open'",
            (shift_id,),
        )
        if shift:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Gunakan POST /pos/shift/close untuk menutup shift dengan kas akhir"},
            )

        return {"success": True, "message": "Shift sudah ditutup atau tidak ditemukan"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ── GET /pos/shifts (legacy compat) ────────────────────────────────
@router.get("/pos/shifts")
async def list_shifts():
    """List active shifts."""
    rows = fetch_all(
        "SELECT * FROM pos_cashier_shift WHERE status = 'open' ORDER BY opened_at DESC"
    )
    return {"active_shifts": rows}
