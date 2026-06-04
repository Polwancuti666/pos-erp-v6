"""Finance Router - Beauty & Shine ERP."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

router = APIRouter(prefix="/api/finance", tags=["Finance"])

def generate_doc_key(module: str, branch_code: str = "BSD") -> str:
    today = date.today().strftime("%Y%m%d")
    seq_key = f"SEQ-{module}-{branch_code}-2026"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE document_registry SET sequence = sequence + 1 WHERE doc_key = %s RETURNING sequence", (seq_key,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence) VALUES (%s,%s,%s,%s,1) RETURNING sequence", (seq_key, module, branch_code, date.today()))
                row = cur.fetchone()
            return f"{module}-{branch_code}-{today}-{row['sequence']:04d}"

# ── Journal Entry ─────────────────────────────────────────────────

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

@router.get("/journal-entries")
def list_journal_entries(branch_id: str = "", status: str = "", offset: int = 0, limit: int = 50):
    conditions = []
    params = []
    if branch_id:
        conditions.append("je.branch_id = %s")
        params.append(branch_id)
    if status:
        conditions.append("je.status = %s")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"SELECT je.*, b.name as branch_name FROM journal_entry je LEFT JOIN branch b ON je.branch_id=b.id {where} ORDER BY je.entry_date DESC LIMIT %s OFFSET %s",
        tuple(params)
    )
    return {"items": rows}

@router.post("/journal-entry")
def create_journal_entry(req: JournalEntryReq):
    total_debit = sum(l.debit for l in req.lines)
    total_credit = sum(l.credit for l in req.lines)
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(400, f"Debit ({total_debit}) must equal Credit ({total_credit})")
    
    doc_key = generate_doc_key("JE")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO journal_entry (doc_key, branch_id, entry_date, description, status, total_debit, total_credit)
                   VALUES (%s, %s, %s, %s, 'draft', %s, %s) RETURNING *""",
                (doc_key, req.branch_id, req.entry_date, req.description, total_debit, total_credit)
            )
            je = cur.fetchone()
            for line in req.lines:
                cur.execute(
                    """INSERT INTO journal_entry_line (journal_entry_id, account_code, debit, credit, description)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (je["id"], line.account_code, line.debit, line.credit, line.description)
                )
    return je

@router.put("/journal-entry/{id}/post")
def post_journal_entry(id: str):
    je = fetch_one("SELECT * FROM journal_entry WHERE id = %s", (id,))
    if not je:
        raise HTTPException(404, "Journal entry not found")
    if je["status"] == "posted":
        raise HTTPException(400, "Already posted")
    
    lines = fetch_all("SELECT * FROM journal_entry_line WHERE journal_entry_id = %s", (id,))
    with get_conn() as conn:
        with conn.cursor() as cur:
            for line in lines:
                cur.execute(
                    """INSERT INTO general_ledger (doc_key, branch_id, account_code, debit, credit, balance, transaction_date, description)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (je["doc_key"], je["branch_id"], line["account_code"], float(line["debit"]), float(line["credit"]),
                     float(line["debit"]) - float(line["credit"]), je["entry_date"], line["description"])
                )
            cur.execute("UPDATE journal_entry SET status='posted' WHERE id=%s", (id,))
    return fetch_one("SELECT * FROM journal_entry WHERE id=%s", (id,))

# ── General Ledger ────────────────────────────────────────────────

@router.get("/general-ledger")
def list_gl_entries(account_code: str = "", branch_id: str = "", date_from: str = "", date_to: str = "", offset: int = 0, limit: int = 100):
    conditions = []
    params = []
    if account_code:
        conditions.append("account_code = %s")
        params.append(account_code)
    if branch_id:
        conditions.append("branch_id = %s")
        params.append(branch_id)
    if date_from:
        conditions.append("transaction_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("transaction_date <= %s")
        params.append(date_to)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"SELECT gl.*, coa.account_name FROM general_ledger gl LEFT JOIN chart_of_account coa ON gl.account_code=coa.account_code {where} ORDER BY gl.transaction_date DESC LIMIT %s OFFSET %s",
        tuple(params)
    )
    return {"items": rows}

# ── Trial Balance ─────────────────────────────────────────────────

@router.get("/trial-balance")
def get_trial_balance(branch_id: str = "", period: str = ""):
    conditions = []
    params = []
    if branch_id:
        conditions.append("gl.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = fetch_all(
        f"""SELECT gl.account_code, coa.account_name, coa.account_type,
                   SUM(gl.debit) as total_debit, SUM(gl.credit) as total_credit,
                   SUM(gl.debit) - SUM(gl.credit) as balance
            FROM general_ledger gl
            JOIN chart_of_account coa ON gl.account_code = coa.account_code
            {where}
            GROUP BY gl.account_code, coa.account_name, coa.account_type
            ORDER BY gl.account_code""",
        tuple(params)
    )
    total_debit = sum(float(r["total_debit"]) for r in rows)
    total_credit = sum(float(r["total_credit"]) for r in rows)
    return {"items": rows, "total_debit": total_debit, "total_credit": total_credit}

# ── Profit & Loss ─────────────────────────────────────────────────

@router.get("/profit-loss")
def get_profit_loss(branch_id: str = "", period: str = ""):
    conditions = []
    params = []
    if branch_id:
        conditions.append("gl.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    rows = fetch_all(
        f"""SELECT coa.account_type,
                   SUM(gl.debit) as total_debit, SUM(gl.credit) as total_credit
            FROM general_ledger gl
            JOIN chart_of_account coa ON gl.account_code = coa.account_code
            {where}
            GROUP BY coa.account_type""",
        tuple(params)
    )
    
    result = {"revenue": 0, "cogs": 0, "operating_expenses": 0, "other_income": 0, "other_expense": 0}
    for r in rows:
        if r["account_type"] == "Revenue":
            result["revenue"] += float(r["total_credit"]) - float(r["total_debit"])
        elif r["account_type"] == "Expense":
            result["cogs"] += float(r["total_debit"]) - float(r["total_credit"])
    
    result["gross_profit"] = result["revenue"] - result["cogs"]
    result["net_profit"] = result["gross_profit"]
    return result

# ── Accounts Payable ──────────────────────────────────────────────

@router.get("/accounts-payable")
def list_ap(status: str = "", branch_id: str = "", offset: int = 0, limit: int = 50):
    conditions = []
    params = []
    if status:
        conditions.append("ap.status = %s")
        params.append(status)
    if branch_id:
        conditions.append("ap.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"SELECT ap.*, b.name as branch_name FROM accounts_payable ap LEFT JOIN branch b ON ap.branch_id=b.id {where} ORDER BY ap.due_date LIMIT %s OFFSET %s",
        tuple(params)
    )
    return {"items": rows}

class APRequest(BaseModel):
    supplier_name: str
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    amount: float
    branch_id: str

@router.post("/accounts-payable")
def create_ap(req: APRequest):
    doc_key = generate_doc_key("AP")
    return execute_returning(
        """INSERT INTO accounts_payable (doc_key, supplier_name, invoice_no, invoice_date, due_date, amount, branch_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (doc_key, req.supplier_name, req.invoice_no, req.invoice_date, req.due_date, req.amount, req.branch_id)
    )

class APPaymentRequest(BaseModel):
    payment_date: str
    amount: float
    payment_method_id: Optional[str] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None

@router.post("/ap/{id}/payment")
def record_ap_payment(id: str, req: APPaymentRequest):
    ap = fetch_one("SELECT * FROM accounts_payable WHERE id = %s", (id,))
    if not ap:
        raise HTTPException(404, "AP not found")
    
    new_paid = float(ap["paid_amount"]) + req.amount
    status = "paid" if new_paid >= float(ap["amount"]) else "partial"
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ap_payment (ap_id, payment_date, amount, payment_method_id, reference_no, notes) VALUES (%s,%s,%s,%s,%s,%s)",
                (id, req.payment_date, req.amount, req.payment_method_id, req.reference_no, req.notes)
            )
            cur.execute("UPDATE accounts_payable SET paid_amount=%s, status=%s WHERE id=%s", (new_paid, status, id))
    return fetch_one("SELECT * FROM accounts_payable WHERE id=%s", (id,))

# ── Bank Account ──────────────────────────────────────────────────

@router.get("/bank-accounts")
def list_bank_accounts(branch_id: str = ""):
    if branch_id:
        return {"items": fetch_all("SELECT ba.*, c.code as currency_code FROM bank_account ba LEFT JOIN currency c ON ba.currency_id=c.id WHERE ba.is_active=true AND ba.branch_id=%s", (branch_id,))}
    return {"items": fetch_all("SELECT ba.*, c.code as currency_code, b.name as branch_name FROM bank_account ba LEFT JOIN currency c ON ba.currency_id=c.id LEFT JOIN branch b ON ba.branch_id=b.id WHERE ba.is_active=true")}

class BankAccountReq(BaseModel):
    branch_id: str
    bank_name: str
    account_no: str
    account_name: Optional[str] = None
    currency_id: Optional[str] = None

@router.post("/bank-account")
def create_bank_account(req: BankAccountReq):
    return execute_returning(
        "INSERT INTO bank_account (branch_id, bank_name, account_no, account_name, currency_id) VALUES (%s,%s,%s,%s,%s) RETURNING *",
        (req.branch_id, req.bank_name, req.account_no, req.account_name, req.currency_id)
    )

# ── Bank Transactions ─────────────────────────────────────────────

@router.get("/bank-transactions/{bank_account_id}")
def list_bank_transactions(bank_account_id: str, offset: int = 0, limit: int = 50):
    rows = fetch_all(
        "SELECT * FROM bank_transaction WHERE bank_account_id=%s ORDER BY transaction_date DESC LIMIT %s OFFSET %s",
        (bank_account_id, limit, offset)
    )
    return {"items": rows}

# ── Bank Reconciliation ───────────────────────────────────────────

@router.post("/bank-reconciliation")
def create_reconciliation(bank_account_id: str, period: str = ""):
    doc_key = generate_doc_key("BRC")
    return execute_returning(
        "INSERT INTO bank_reconciliation (bank_account_id, period, status) VALUES (%s,%s,'draft') RETURNING *",
        (bank_account_id, period or date.today().strftime("%Y-%m"))
    )

@router.put("/bank-reconciliation/{id}/match")
def match_reconciliation(id: str, item_ids: list[str] = []):
    for item_id in item_ids:
        execute("UPDATE bank_reconciliation_item SET status='matched' WHERE id=%s AND reconciliation_id=%s", (item_id, id))
    return fetch_one("SELECT * FROM bank_reconciliation WHERE id=%s", (id,))

# ── Chart of Account ──────────────────────────────────────────────

@router.get("/chart-of-account")
def get_coa_tree():
    rows = fetch_all("SELECT * FROM chart_of_account WHERE is_active=true ORDER BY account_code")
    return {"items": rows}
