from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# ── Staff Database (mock) ──────────────────────────────────────────
STAFF_DB: dict[str, dict] = {
    "KSR001": {"name": "Siti Nurhaliza", "pin": "1234", "role": "cashier", "branch": "HQ"},
    "KSR002": {"name": "Dewi Lestari", "pin": "5678", "role": "cashier", "branch": "HQ"},
    "ADM001": {"name": "Admin Utama", "pin": "0000", "role": "admin", "branch": "HQ"},
    "MGR001": {"name": "Manager Toko", "pin": "9999", "role": "manager", "branch": "HQ"},
}

# ── Active Shifts (in-memory, reset on restart) ────────────────────
ACTIVE_SHIFTS: dict[str, dict] = {}


@router.post("/pos/auth")
async def pos_auth(request: Request):
    """Authenticate staff and start shift."""
    try:
        data = await request.json()
        staff_id = (data.get("staff_id") or "").strip().upper()
        pin = (data.get("pin") or "").strip()

        if not staff_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Staff ID wajib diisi"},
            )

        staff = STAFF_DB.get(staff_id)
        if not staff:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": f"Staff ID '{staff_id}' tidak ditemukan"},
            )

        if staff["pin"] != pin:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "PIN salah"},
            )

        # Start shift
        import datetime
        shift_id = f"SHIFT-{staff_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        ACTIVE_SHIFTS[shift_id] = {
            "shift_id": shift_id,
            "staff_id": staff_id,
            "name": staff["name"],
            "role": staff["role"],
            "branch": staff["branch"],
            "started_at": datetime.datetime.now().isoformat(),
        }

        return {
            "success": True,
            "message": f"Selamat datang, {staff['name']}!",
            "shift_id": shift_id,
            "staff": {
                "id": staff_id,
                "name": staff["name"],
                "role": staff["role"],
                "branch": staff["branch"],
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)},
        )


@router.post("/pos/end-shift")
async def pos_end_shift(request: Request):
    """End an active shift."""
    try:
        data = await request.json()
        shift_id = data.get("shift_id", "")

        if shift_id in ACTIVE_SHIFTS:
            shift = ACTIVE_SHIFTS.pop(shift_id)
            return {
                "success": True,
                "message": f"Shift {shift['name']} telah berakhir.",
            }
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Shift tidak ditemukan"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)},
        )


@router.get("/pos/shifts")
async def list_shifts():
    """List all active shifts."""
    return {"active_shifts": list(ACTIVE_SHIFTS.values())}
