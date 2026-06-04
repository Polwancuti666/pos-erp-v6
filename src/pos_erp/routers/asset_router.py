"""Asset Management Module Router for Beauty & Shine POS-ERP V6."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/asset", tags=["Asset Management"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class AssetReq(BaseModel):
    asset_code: str
    name: str
    category: str = ""
    description: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: float = 0
    useful_life_months: int = 0
    depreciation_method: str = "straight_line"  # straight_line | declining_balance
    salvage_value: float = 0
    location: Optional[str] = None
    status: str = "active"


class DepreciateReq(BaseModel):
    period_date: date
    override_amount: Optional[float] = None  # manually override calculated amount


class MaintenanceReq(BaseModel):
    maintenance_date: date
    description: str
    cost: float = 0
    vendor: Optional[str] = None
    next_maintenance_date: Optional[date] = None
    notes: Optional[str] = None


class DisposeReq(BaseModel):
    dispose_date: date
    disposal_method: str = "sold"  # sold | scrapped | donated
    disposal_price: float = 0
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Asset CRUD
# ---------------------------------------------------------------------------

@router.get("/summary")
def asset_summary():
    """Get asset summary: total value, depreciation, breakdown by category."""
    totals = fetch_one(
        "SELECT "
        "  COUNT(*) AS total_assets, "
        "  COALESCE(SUM(purchase_cost), 0) AS total_purchase_cost "
        "FROM asset WHERE status != 'disposed'"
    )

    total_depreciated = fetch_one(
        "SELECT COALESCE(SUM(amount), 0) AS total_depreciation "
        "FROM asset_depreciation"
    )

    by_category = fetch_all(
        "SELECT category, COUNT(*) AS count, "
        "  COALESCE(SUM(purchase_cost), 0) AS total_purchase_cost "
        "FROM asset WHERE status != 'disposed' "
        "GROUP BY category ORDER BY total_purchase_cost DESC"
    )

    return {
        "total_assets": totals["total_assets"] if totals else 0,
        "total_purchase_cost": totals["total_purchase_cost"] if totals else 0,
        "total_depreciation": total_depreciated["total_depreciation"] if total_depreciated else 0,
        "net_book_value": (
            (totals["total_purchase_cost"] if totals else 0)
            - (total_depreciated["total_depreciation"] if total_depreciated else 0)
        ),
        "by_category": by_category,
    }


@router.get("")
def list_assets():
    """List all assets."""
    rows = fetch_all("SELECT * FROM asset ORDER BY purchase_date DESC NULLS LAST")
    return {"items": rows}


@router.get("/{asset_id}")
def get_asset(asset_id: int):
    """Get a single asset by ID."""
    row = fetch_one("SELECT * FROM asset WHERE id = %s", (asset_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    return row


@router.post("")
def create_asset(req: AssetReq):
    """Create a new asset."""
    existing = fetch_one(
        "SELECT id FROM asset WHERE asset_code = %s", (req.asset_code,)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Asset code already exists")

    row = execute_returning(
        "INSERT INTO asset "
        "(asset_code, name, category, description, purchase_date, purchase_cost, "
        "useful_life_months, depreciation_method, salvage_value, location, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
        (
            req.asset_code,
            req.name,
            req.category,
            req.description,
            req.purchase_date,
            req.purchase_cost,
            req.useful_life_months,
            req.depreciation_method,
            req.salvage_value,
            req.location,
            req.status,
        ),
    )
    return row


@router.put("/{asset_id}")
def update_asset(asset_id: int, req: AssetReq):
    """Update an existing asset."""
    existing = fetch_one("SELECT id FROM asset WHERE id = %s", (asset_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Asset not found")

    row = execute_returning(
        "UPDATE asset SET "
        "asset_code=%s, name=%s, category=%s, description=%s, "
        "purchase_date=%s, purchase_cost=%s, useful_life_months=%s, "
        "depreciation_method=%s, salvage_value=%s, location=%s, status=%s, "
        "updated_at=NOW() "
        "WHERE id=%s RETURNING *",
        (
            req.asset_code,
            req.name,
            req.category,
            req.description,
            req.purchase_date,
            req.purchase_cost,
            req.useful_life_months,
            req.depreciation_method,
            req.salvage_value,
            req.location,
            req.status,
            asset_id,
        ),
    )
    return row


# ---------------------------------------------------------------------------
# Depreciation
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/depreciate")
def depreciate_asset(asset_id: int, req: DepreciateReq):
    """Calculate and record monthly depreciation for an asset."""
    asset = fetch_one("SELECT * FROM asset WHERE id = %s", (asset_id,))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset["status"] == "disposed":
        raise HTTPException(status_code=400, detail="Cannot depreciate a disposed asset")
    if asset["useful_life_months"] <= 0:
        raise HTTPException(status_code=400, detail="Asset has no useful life defined")

    # Check if already depreciated for this period
    dup = fetch_one(
        "SELECT id FROM asset_depreciation WHERE asset_id=%s AND period_date=%s",
        (asset_id, req.period_date),
    )
    if dup:
        raise HTTPException(
            status_code=400,
            detail="Depreciation already recorded for this period",
        )

    # Get cumulative depreciation so far
    agg = fetch_one(
        "SELECT COALESCE(SUM(amount), 0) AS total_depr "
        "FROM asset_depreciation WHERE asset_id = %s",
        (asset_id,),
    )
    total_depr = agg["total_depr"] if agg else 0

    depreciable_base = asset["purchase_cost"] - asset["salvage_value"]

    if req.override_amount is not None:
        amount = req.override_amount
    elif asset["depreciation_method"] == "declining_balance":
        # Declining balance: 2 / life * (cost - accumulated)
        book_value = asset["purchase_cost"] - total_depr
        rate = 2.0 / asset["useful_life_months"]
        amount = round(book_value * rate, 2)
    else:
        # Straight-line
        amount = round(depreciable_base / asset["useful_life_months"], 2)

    # Don't depreciate below salvage value
    if total_depr + amount > depreciable_base:
        amount = round(depreciable_base - total_depr, 2)

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Asset is fully depreciated")

    row = execute_returning(
        "INSERT INTO asset_depreciation "
        "(asset_id, period_date, amount, method, created_at) "
        "VALUES (%s, %s, %s, %s, NOW()) RETURNING *",
        (asset_id, req.period_date, amount, asset["depreciation_method"]),
    )
    return row


@router.get("/{asset_id}/depreciation-history")
def depreciation_history(asset_id: int):
    """Get depreciation history for an asset."""
    asset = fetch_one("SELECT id FROM asset WHERE id = %s", (asset_id,))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    rows = fetch_all(
        "SELECT * FROM asset_depreciation "
        "WHERE asset_id = %s ORDER BY period_date DESC",
        (asset_id,),
    )
    return {"items": rows}


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/maintenance")
def log_maintenance(asset_id: int, req: MaintenanceReq):
    """Log a maintenance event for an asset."""
    asset = fetch_one("SELECT id FROM asset WHERE id = %s", (asset_id,))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    row = execute_returning(
        "INSERT INTO asset_maintenance "
        "(asset_id, maintenance_date, description, cost, vendor, "
        "next_maintenance_date, notes, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()) RETURNING *",
        (
            asset_id,
            req.maintenance_date,
            req.description,
            req.cost,
            req.vendor,
            req.next_maintenance_date,
            req.notes,
        ),
    )
    return row


@router.get("/{asset_id}/maintenance-history")
def maintenance_history(asset_id: int):
    """Get maintenance history for an asset."""
    asset = fetch_one("SELECT id FROM asset WHERE id = %s", (asset_id,))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    rows = fetch_all(
        "SELECT * FROM asset_maintenance "
        "WHERE asset_id = %s ORDER BY maintenance_date DESC",
        (asset_id,),
    )
    return {"items": rows}


# ---------------------------------------------------------------------------
# Disposal
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/dispose")
def dispose_asset(asset_id: int, req: DisposeReq):
    """Dispose of an asset, calculating gain/loss."""
    asset = fetch_one("SELECT * FROM asset WHERE id = %s", (asset_id,))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset["status"] == "disposed":
        raise HTTPException(status_code=400, detail="Asset is already disposed")

    # Get accumulated depreciation
    agg = fetch_one(
        "SELECT COALESCE(SUM(amount), 0) AS total_depr "
        "FROM asset_depreciation WHERE asset_id = %s",
        (asset_id,),
    )
    total_depr = agg["total_depr"] if agg else 0

    book_value = asset["purchase_cost"] - total_depr
    gain_loss = req.disposal_price - book_value

    row = execute_returning(
        "UPDATE asset SET status='disposed', disposal_date=%s, "
        "disposal_method=%s, disposal_price=%s, updated_at=NOW() "
        "WHERE id=%s RETURNING *",
        (req.dispose_date, req.disposal_method, req.disposal_price, asset_id),
    )

    return {
        **row,
        "book_value_at_disposal": book_value,
        "accumulated_depreciation": total_depr,
        "gain_loss": gain_loss,
        "disposal_notes": req.notes,
    }
