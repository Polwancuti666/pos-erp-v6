"""Finance Router - Beauty & Shine ERP.

Domain-driven implementation with:
- Journal/JournalLine for double-entry accounting
- COAMapping for auto-journal
- General Ledger with trial balance
- Accounts Payable management
- Bank reconciliation
- AuditTrail integration
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.domain_models import (
    DocumentKind, JournalStatus, AccountType, AuditAction,
    money, JournalLine, AccountingException,
)
from pos_erp.repository import (
    DocumentRegistryRepository, AuditTrailRepository,
    JournalEntryRepository, GeneralLedgerRepository,
    AccountsPayableRepository, BankRepository,
)
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

router = APIRouter(prefix="/api/finance", tags=["Finance"])

# ── Request Models ────────────────────────────────────────────────

class JournalLineReq(BaseModel):
    account_code: str
    debit: float = 0
    credit: float = 0
    description: Optional[str] = None

class JournalEntryReq(BaseModel):
    branch_id: str
    entry_date: str
    description: Optional[str] = None
    lines: list[JournalLineReq]
    created_by: Optional[str] = None

class APRequest(BaseModel):
    supplier_name: str
    amount: float
    branch_id: str
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None

class APPaymentRequest(BaseModel):
    payment_date: str
    amount: float
    payment_method_id: Optional[str] = None
    reference_no: Optional[str] = None

class BankAccountReq(BaseModel):
    branch_id: str
    bank_name: str
    account_no: str
    account_name: Optional[str] = None
    currency_id: Optional[str] = None

class ReconciliationReq(BaseModel):
    bank_account_id: str
    period: str


# ── Helpers ───────────────────────────────────────────────────────

def _generate_doc_key(module: DocumentKind, branch_code: str = "BSD") -> str:
    return DocumentRegistryRepository.generate_doc_key(module.value, branch_code)

def _audit(doc_key: str, action: AuditAction, details: str = None):
    AuditTrailRepository.record(doc_key=doc_key, module="finance", action=action.value, new_value=details)


# ── Journal Entry ─────────────────────────────────────────────────

@router.get("/journal-entries")
def list_journal_entries(branch_id: str = "", status: str = "", offset: int = 0, limit: int = 50):
    """List journal entries with filters."""
    return {"items": JournalEntryRepository.list_entries(branch_id or None, status or None, offset, limit)}

@router.post("/journal-entry")
def create_journal_entry(req: JournalEntryReq):
    """Create journal entry with lines. Validates debit = credit."""
    # Validate balance
    total_debit = sum(l.debit for l in req.lines)
    total_credit = sum(l.credit for l in req.lines)
    
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(400, f"Debit ({total_debit}) must equal Credit ({total_credit})")
    
    doc_key = _generate_doc_key(DocumentKind.JE)
    
    je = JournalEntryRepository.create(
        doc_key=doc_key,
        branch_id=req.branch_id,
        entry_date=req.entry_date,
        description=req.description,
        created_by=req.created_by,
    )
    
    for line in req.lines:
        JournalEntryRepository.add_line(je["id"], line.account_code, line.debit, line.credit, line.description)
    
    _audit(doc_key, AuditAction.CREATE, f"Journal entry created: {req.description}")
    
    return JournalEntryRepository.get(je["id"])

@router.put("/journal-entry/{id}/post")
def post_journal_entry(id: str):
    """Post journal entry to General Ledger."""
    try:
        je = JournalEntryRepository.post(id)
        _audit(je["doc_key"], AuditAction.POST, "Journal entry posted to GL")
        return je
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/journal-entry/{id}")
def get_journal_entry(id: str):
    """Get journal entry with lines."""
    je = JournalEntryRepository.get(id)
    if not je:
        raise HTTPException(404, "Journal entry not found")
    return je


# ── General Ledger ────────────────────────────────────────────────

@router.get("/general-ledger")
def list_gl_entries(
    account_code: str = "",
    branch_id: str = "",
    date_from: str = "",
    date_to: str = "",
    offset: int = 0,
    limit: int = 100,
):
    """List General Ledger entries."""
    return {"items": GeneralLedgerRepository.get_entries(
        account_code=account_code or None,
        branch_id=branch_id or None,
        date_from=date_from or None,
        date_to=date_to or None,
        offset=offset,
        limit=limit,
    )}

@router.get("/trial-balance")
def get_trial_balance(branch_id: str = ""):
    """Get trial balance grouped by account."""
    return GeneralLedgerRepository.get_trial_balance(branch_id or None)

@router.get("/profit-loss")
def get_profit_loss(branch_id: str = ""):
    """Get Profit & Loss statement."""
    return GeneralLedgerRepository.get_profit_loss(branch_id or None)


# ── Accounts Payable ──────────────────────────────────────────────

@router.get("/accounts-payable")
def list_ap(status: str = "", branch_id: str = "", offset: int = 0, limit: int = 50):
    """List Accounts Payable."""
    return {"items": AccountsPayableRepository.list_ap(status or None, branch_id or None, offset, limit)}

@router.post("/accounts-payable")
def create_ap(req: APRequest):
    """Create Accounts Payable entry."""
    doc_key = _generate_doc_key(DocumentKind.AP)
    ap = AccountsPayableRepository.create(
        doc_key=doc_key,
        supplier_name=req.supplier_name,
        amount=req.amount,
        branch_id=req.branch_id,
        invoice_no=req.invoice_no,
        invoice_date=req.invoice_date,
        due_date=req.due_date,
    )
    _audit(doc_key, AuditAction.CREATE, f"AP created: {req.supplier_name} - {req.amount}")
    return ap

@router.post("/ap/{id}/payment")
def record_ap_payment(id: str, req: APPaymentRequest):
    """Record AP payment."""
    try:
        ap = AccountsPayableRepository.record_payment(
            ap_id=id,
            amount=req.amount,
            payment_date=req.payment_date,
            payment_method_id=req.payment_method_id,
            reference_no=req.reference_no,
        )
        _audit(ap["doc_key"], AuditAction.UPDATE, f"AP payment: {req.amount}")
        return ap
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Bank Account ──────────────────────────────────────────────────

@router.get("/bank-accounts")
def list_bank_accounts(branch_id: str = ""):
    """List bank accounts."""
    return {"items": BankRepository.list_accounts(branch_id or None)}

@router.post("/bank-account")
def create_bank_account(req: BankAccountReq):
    """Create bank account."""
    return BankRepository.create_account(
        branch_id=req.branch_id,
        bank_name=req.bank_name,
        account_no=req.account_no,
        account_name=req.account_name,
        currency_id=req.currency_id,
    )

@router.get("/bank-transactions/{bank_account_id}")
def list_bank_transactions(bank_account_id: str, offset: int = 0, limit: int = 50):
    """List bank transactions."""
    return {"items": BankRepository.get_transactions(bank_account_id, offset, limit)}


# ── Bank Reconciliation ──────────────────────────────────────────

@router.get("/reconciliation")
def list_reconciliations(bank_account_id: str = ""):
    """List bank reconciliations."""
    if bank_account_id:
        rows = fetch_all("SELECT * FROM bank_reconciliation WHERE bank_account_id = %s ORDER BY period DESC", (bank_account_id,))
    else:
        rows = fetch_all("SELECT br.*, ba.bank_name, ba.account_no FROM bank_reconciliation br JOIN bank_account ba ON br.bank_account_id=ba.id ORDER BY br.period DESC")
    return {"items": rows}

@router.post("/reconciliation")
def create_reconciliation(req: ReconciliationReq):
    """Create bank reconciliation."""
    doc_key = _generate_doc_key(DocumentKind.BRC)
    return execute_returning(
        "INSERT INTO bank_reconciliation (bank_account_id, period, status) VALUES (%s, %s, 'draft') RETURNING *",
        (req.bank_account_id, req.period)
    )

@router.put("/reconciliation/{id}/match")
def match_reconciliation_items(id: str, item_ids: list[str] = []):
    """Match reconciliation items."""
    for item_id in item_ids:
        execute("UPDATE bank_reconciliation_item SET status='matched' WHERE id=%s AND reconciliation_id=%s", (item_id, id))
    return fetch_one("SELECT * FROM bank_reconciliation WHERE id=%s", (id,))


# ── Chart of Account ──────────────────────────────────────────────

@router.get("/chart-of-account")
def get_coa_tree(account_type: str = ""):
    """Get Chart of Accounts tree."""
    if account_type:
        return {"items": fetch_all("SELECT * FROM chart_of_account WHERE is_active=true AND account_type=%s ORDER BY account_code", (account_type,))}
    return {"items": fetch_all("SELECT * FROM chart_of_account WHERE is_active=true ORDER BY account_code")}


# ── Account Mapping ───────────────────────────────────────────────

@router.get("/account-mapping")
def list_account_mappings(module: str = ""):
    """List account mappings for auto-journal."""
    if module:
        return {"items": fetch_all("SELECT * FROM account_mapping WHERE module=%s", (module,))}
    return {"items": fetch_all("SELECT * FROM account_mapping ORDER BY module, transaction_type")}


# ── Asset Management ──────────────────────────────────────────────

@router.get("/assets")
def list_assets(branch_id: str = "", status: str = ""):
    """List fixed assets."""
    conditions = []
    params = []
    if branch_id:
        conditions.append("a.branch_id = %s")
        params.append(branch_id)
    if status:
        conditions.append("a.status = %s")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    rows = fetch_all(
        f"SELECT a.*, b.name as branch_name FROM asset a LEFT JOIN branch b ON a.branch_id=b.id {where} ORDER BY a.purchase_date DESC",
        tuple(params)
    )
    return {"items": rows}

class AssetRequest(BaseModel):
    name: str
    category: Optional[str] = None
    purchase_date: str
    purchase_cost: float
    salvage_value: float = 0
    useful_life_months: int = 0
    depreciation_method: str = "straight_line"
    branch_id: str

@router.post("/asset")
def create_asset(req: AssetRequest):
    """Create fixed asset."""
    doc_key = _generate_doc_key(DocumentKind.FA)
    return execute_returning(
        """INSERT INTO asset (doc_key, name, category, purchase_date, purchase_cost, salvage_value, useful_life_months, depreciation_method, branch_id, current_value)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
        (doc_key, req.name, req.category, req.purchase_date, req.purchase_cost, req.salvage_value,
         req.useful_life_months, req.depreciation_method, req.branch_id, req.purchase_cost)
    )

@router.post("/asset/{id}/depreciate")
def depreciate_asset(id: str, period: str = ""):
    """Calculate depreciation for an asset."""
    asset = fetch_one("SELECT * FROM asset WHERE id = %s", (id,))
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    if asset["depreciation_method"] == "straight_line":
        monthly_depr = (float(asset["purchase_cost"]) - float(asset["salvage_value"])) / int(asset["useful_life_months"])
        accumulated = fetch_one(
            "SELECT COALESCE(SUM(depreciation_amount), 0) as total FROM asset_depreciation WHERE asset_id = %s",
            (id,)
        )
        acc_total = float(accumulated["total"]) + monthly_depr
        book_value = float(asset["purchase_cost"]) - acc_total
        
        execute_returning(
            """INSERT INTO asset_depreciation (asset_id, period, depreciation_amount, accumulated_depreciation, book_value)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (id, period or date.today().strftime("%Y-%m"), monthly_depr, acc_total, book_value)
        )
        
        execute("UPDATE asset SET current_value = %s WHERE id = %s", (book_value, id))
    
    return fetch_one("SELECT * FROM asset WHERE id = %s", (id,))


# ── Profit & Loss (Extended) ──────────────────────────────────────

@router.get("/pnl-detail")
def get_pnl_detail(branch_id: str = "", period: str = ""):
    """Get detailed P&L breakdown."""
    conditions = []
    params = []
    if branch_id:
        conditions.append("gl.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Revenue breakdown
    revenue = fetch_all(
        f"""SELECT coa.account_name, SUM(gl.credit) - SUM(gl.debit) as amount
            FROM general_ledger gl
            JOIN chart_of_account coa ON gl.account_code = coa.account_code
            {where} {'AND' if where else 'WHERE'} coa.account_type = 'Revenue'
            GROUP BY coa.account_name ORDER BY amount DESC""",
        tuple(params)
    )
    
    # Expense breakdown
    expenses = fetch_all(
        f"""SELECT coa.account_name, SUM(gl.debit) - SUM(gl.credit) as amount
             FROM general_ledger gl
             JOIN chart_of_account coa ON gl.account_code = coa.account_code
             {where} {'AND' if where else 'WHERE'} coa.account_type = 'Expense'
             GROUP BY coa.account_name ORDER BY amount DESC""",
        tuple(params)
    )
    
    total_revenue = sum(float(r["amount"]) for r in revenue)
    total_expense = sum(float(r["amount"]) for r in expenses)
    
    return {
        "revenue": revenue,
        "expenses": expenses,
        "total_revenue": total_revenue,
        "total_expense": total_expense,
        "net_profit": total_revenue - total_expense,
    }
