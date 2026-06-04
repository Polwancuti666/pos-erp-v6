"""PostgreSQL-backed repository for domain entities.

Implements the Repository pattern to replace InMemoryRepository.
Each entity type has its own table and serialization logic.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, TypeVar, Generic
from dataclasses import asdict, dataclass

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

T = TypeVar("T")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            # Always include timezone (UTC) so JS Date parses correctly
            if obj.tzinfo is None:
                return obj.isoformat() + '+00:00'
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


# ── Document Registry Repository ──────────────────────────────────

class DocumentRegistryRepository:
    """Manages document key generation and cross-references."""
    
    @staticmethod
    def generate_doc_key(module: str, branch_code: str = "BSD") -> str:
        """Generate unique doc key: MODULE-BRANCH-YYYYMMDD-NNNNNN
        
        Also registers the generated doc_key in document_registry so that
        FK constraints in dependent tables (pos_transaction, journal_entry,
        stock_movement, etc.) are satisfied.
        """
        today = date.today().strftime("%Y%m%d")
        seq_key = f"SEQ-{module}-{branch_code}-{date.today().year}"
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE document_registry SET sequence = sequence + 1 WHERE doc_key = %s RETURNING sequence",
                    (seq_key,)
                )
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        "INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence) VALUES (%s, %s, %s, %s, 1) RETURNING sequence",
                        (seq_key, module, branch_code, date.today())
                    )
                    row = cur.fetchone()
                seq = row["sequence"]
                
                doc_key = f"{module}-{branch_code}-{today}-{seq:06d}"
                
                # Register the actual doc_key so FK constraints in dependent
                # tables are satisfied before any INSERT referencing it.
                cur.execute(
                    "INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence, status) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (doc_key) DO NOTHING",
                    (doc_key, module, branch_code, date.today(), seq, "active")
                )
        
        return doc_key
    
    @staticmethod
    def register(doc_key: str, module: str, branch_code: str, status: str = "active") -> dict:
        """Register a document in the registry."""
        return execute_returning(
            """INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence, status)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (doc_key, module, branch_code, date.today(), 0, status)
        )
    
    @staticmethod
    def link(source_doc_key: str, target_doc_key: str, link_type: str) -> dict:
        """Create cross-reference between documents."""
        return execute_returning(
            "INSERT INTO document_cross_reference (source_doc_key, target_doc_key, link_type) VALUES (%s, %s, %s) RETURNING *",
            (source_doc_key, target_doc_key, link_type)
        )
    
    @staticmethod
    def get_links(doc_key: str) -> list[dict]:
        """Get all cross-references for a document."""
        return fetch_all(
            """SELECT * FROM document_cross_reference 
               WHERE source_doc_key = %s OR target_doc_key = %s""",
            (doc_key, doc_key)
        )


# ── Audit Trail Repository ────────────────────────────────────────

class AuditTrailRepository:
    """Records all changes for audit purposes."""
    
    @staticmethod
    def record(
        doc_key: str,
        module: str,
        action: str,
        user_id: str = None,
        user_name: str = None,
        field_name: str = None,
        old_value: str = None,
        new_value: str = None,
        ip_address: str = None,
    ) -> dict:
        return execute_returning(
            """INSERT INTO audit_trail (doc_key, module, action, user_id, user_name, field_name, old_value, new_value, ip_address)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (doc_key, module, action, user_id, user_name, field_name, old_value, new_value, ip_address)
        )
    
    @staticmethod
    def get_by_doc(doc_key: str) -> list[dict]:
        return fetch_all("SELECT * FROM audit_trail WHERE doc_key = %s ORDER BY timestamp DESC", (doc_key,))
    
    @staticmethod
    def get_by_module(module: str, limit: int = 100) -> list[dict]:
        return fetch_all("SELECT * FROM audit_trail WHERE module = %s ORDER BY timestamp DESC LIMIT %s", (module, limit))


# ── Transaction Repository ────────────────────────────────────────

class TransactionRepository:
    """POS transaction persistence."""
    
    @staticmethod
    def create(
        doc_key: str,
        branch_id: str,
        customer_name: str = None,
        customer_phone: str = None,
        status: str = "open",
        cashier_id: str = None,
        booking_date: str = None,
        booking_time: str = None,
        notes: str = None,
    ) -> dict:
        return execute_returning(
            """INSERT INTO pos_transaction (doc_key, branch_id, customer_name, customer_phone, status, cashier_id, booking_date, booking_time, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (doc_key, branch_id, customer_name, customer_phone, status, cashier_id, booking_date, booking_time, notes)
        )
    
    @staticmethod
    def get(transaction_id: str) -> dict | None:
        return fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (transaction_id,))
    
    @staticmethod
    def get_by_doc_key(doc_key: str) -> dict | None:
        return fetch_one("SELECT * FROM pos_transaction WHERE doc_key = %s", (doc_key,))
    
    @staticmethod
    def list_transactions(
        branch_id: str = None,
        status: str = None,
        date_from: str = None,
        date_to: str = None,
        q: str = None,
        type: str = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        conditions = []
        params = []
        if branch_id:
            conditions.append("t.branch_id = %s")
            params.append(branch_id)
        if status:
            if ',' in status:
                status_list = [s.strip() for s in status.split(',') if s.strip()]
                placeholders = ','.join(['%s'] * len(status_list))
                conditions.append(f"t.status IN ({placeholders})")
                params.extend(status_list)
            else:
                conditions.append("t.status = %s")
                params.append(status)
        if type == 'booking':
            conditions.append("t.status = 'booked'")
        if date_from:
            conditions.append("t.created_at >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("t.created_at <= %s")
            params.append(date_to + " 23:59:59")
        if q:
            conditions.append("(t.customer_name ILIKE %s OR t.doc_key ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        
        return fetch_all(
            f"""SELECT t.*, b.name as branch_name, u.full_name as cashier_name
                FROM pos_transaction t
                LEFT JOIN branch b ON t.branch_id=b.id
                LEFT JOIN app_user u ON t.cashier_id=u.id
                {where} ORDER BY t.created_at DESC LIMIT %s OFFSET %s""",
            tuple(params)
        )
    
    @staticmethod
    def update_totals(transaction_id: str, subtotal: float, discount: float, tax: float, total: float) -> None:
        execute(
            "UPDATE pos_transaction SET subtotal=%s, discount=%s, tax=%s, total=%s WHERE id=%s",
            (subtotal, discount, tax, total, transaction_id)
        )
    
    @staticmethod
    def update_status(transaction_id: str, status: str, payment_method_id: str = None) -> dict:
        if payment_method_id:
            return execute_returning(
                "UPDATE pos_transaction SET status=%s, payment_method_id=%s WHERE id=%s RETURNING *",
                (status, payment_method_id, transaction_id)
            )
        return execute_returning(
            "UPDATE pos_transaction SET status=%s WHERE id=%s RETURNING *",
            (status, transaction_id)
        )


# ── Transaction Item Repository ───────────────────────────────────

class TransactionItemRepository:
    """POS transaction line items."""
    
    @staticmethod
    def add(
        transaction_id: str,
        item_type: str,
        item_id: str,
        item_name: str,
        qty: float = 1,
        unit_price: float = 0,
        discount: float = 0,
    ) -> dict:
        total = (unit_price * qty) - discount
        return execute_returning(
            """INSERT INTO pos_transaction_item (transaction_id, item_type, item_id, item_name, qty, unit_price, discount, total)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (transaction_id, item_type, item_id, item_name, qty, unit_price, discount, total)
        )
    
    @staticmethod
    def remove(item_id: str, transaction_id: str) -> None:
        execute("DELETE FROM pos_transaction_item WHERE id = %s AND transaction_id = %s", (item_id, transaction_id))
    
    @staticmethod
    def get_by_transaction(transaction_id: str) -> list[dict]:
        return fetch_all("SELECT * FROM pos_transaction_item WHERE transaction_id = %s ORDER BY created_at", (transaction_id,))
    
    @staticmethod
    def get_subtotal(transaction_id: str) -> float:
        result = fetch_one(
            "SELECT COALESCE(SUM(total), 0) as subtotal FROM pos_transaction_item WHERE transaction_id = %s",
            (transaction_id,)
        )
        return float(result["subtotal"])


# ── Treatment Record Repository ───────────────────────────────────

class TreatmentRecordRepository:
    """Treatment session records."""
    
    @staticmethod
    def create(
        doc_key: str,
        transaction_id: str,
        treatment_id: str,
        therapist_id: str = None,
        bed_id: str = None,
        status: str = "scheduled",
        notes: str | None = None,
    ) -> dict:
        return execute_returning(
            """INSERT INTO treatment_record (doc_key, transaction_id, treatment_id, therapist_id, bed_id, status, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (doc_key, transaction_id, treatment_id, therapist_id, bed_id, status, notes)
        )
    
    @staticmethod
    def get(treatment_record_id: str) -> dict | None:
        return fetch_one("SELECT * FROM treatment_record WHERE id = %s", (treatment_record_id,))
    
    @staticmethod
    def get_by_transaction(transaction_id: str) -> list[dict]:
        return fetch_all(
            """SELECT tr.*, t.name as treatment_name, u.full_name as therapist_name, b.name as bed_name
               FROM treatment_record tr
               LEFT JOIN treatment t ON tr.treatment_id=t.id
               LEFT JOIN app_user u ON tr.therapist_id=u.id
               LEFT JOIN bed b ON tr.bed_id=b.id
               WHERE tr.transaction_id = %s""",
            (transaction_id,)
        )
    
    @staticmethod
    def update_status(record_id: str, status: str) -> dict:
        return execute_returning("UPDATE treatment_record SET status=%s WHERE id=%s RETURNING *", (status, record_id))
    
    @staticmethod
    def complete(record_id: str, notes: str = None, before_photo: str = None, after_photo: str = None) -> dict:
        return execute_returning(
            """UPDATE treatment_record SET status='completed', end_time=NOW(), notes=%s, before_photo_url=%s, after_photo_url=%s
               WHERE id=%s RETURNING *""",
            (notes, before_photo, after_photo, record_id)
        )


# ── Stock Repository ──────────────────────────────────────────────

class StockRepository:
    """Inventory stock management."""
    
    @staticmethod
    def get_card(product_id: str, branch_id: str) -> dict | None:
        return fetch_one(
            "SELECT * FROM stock_card WHERE product_id = %s AND branch_id = %s",
            (product_id, branch_id)
        )
    
    @staticmethod
    def get_or_create_card(product_id: str, branch_id: str) -> dict:
        card = StockRepository.get_card(product_id, branch_id)
        if card:
            return card
        return execute_returning(
            """INSERT INTO stock_card (product_id, branch_id, qty_in, qty_out, balance, last_movement_date)
               VALUES (%s, %s, 0, 0, 0, %s) RETURNING *""",
            (product_id, branch_id, date.today())
        )
    
    @staticmethod
    def update_balance(product_id: str, branch_id: str, qty_change: float, movement_type: str) -> dict:
        """Update stock card balance. movement_type: 'in' or 'out'"""
        card = StockRepository.get_or_create_card(product_id, branch_id)
        
        if movement_type == "in":
            new_balance = float(card["balance"]) + qty_change
            execute(
                "UPDATE stock_card SET qty_in = qty_in + %s, balance = %s, last_movement_date = %s WHERE id = %s",
                (qty_change, new_balance, date.today(), card["id"])
            )
        else:
            new_balance = float(card["balance"]) - qty_change
            if new_balance < 0:
                raise ValueError(f"Insufficient stock: available {card['balance']}, required {qty_change}")
            execute(
                "UPDATE stock_card SET qty_out = qty_out + %s, balance = %s, last_movement_date = %s WHERE id = %s",
                (qty_change, new_balance, date.today(), card["id"])
            )
        
        return fetch_one("SELECT * FROM stock_card WHERE id = %s", (card["id"],))
    
    @staticmethod
    def create_movement(
        doc_key: str,
        product_id: str,
        branch_id: str,
        movement_type: str,
        qty: float,
        batch_id: str = None,
        reference_doc_key: str = None,
        notes: str = None,
        created_by: str = None,
    ) -> dict:
        return execute_returning(
            """INSERT INTO stock_movement (doc_key, product_id, batch_id, branch_id, movement_type, qty, reference_doc_key, notes, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (doc_key, product_id, batch_id, branch_id, movement_type, qty, reference_doc_key, notes, created_by)
        )
    
    @staticmethod
    def get_movements(product_id: str = None, branch_id: str = None, limit: int = 100) -> list[dict]:
        conditions = []
        params = []
        if product_id:
            conditions.append("sm.product_id = %s")
            params.append(product_id)
        if branch_id:
            conditions.append("sm.branch_id = %s")
            params.append(branch_id)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        
        return fetch_all(
            f"""SELECT sm.*, p.name as product_name, p.sku
                FROM stock_movement sm
                JOIN product p ON sm.product_id=p.id
                {where} ORDER BY sm.created_at DESC LIMIT %s""",
            tuple(params)
        )
    
    @staticmethod
    def get_low_stock(branch_id: str = None, threshold: float = 10) -> list[dict]:
        extra = "AND sc.branch_id = %s" if branch_id else ""
        params = (threshold,) + ((branch_id,) if branch_id else ())
        return fetch_all(
            f"""SELECT sc.*, p.name as product_name, p.sku, b.name as branch_name
                FROM stock_card sc
                JOIN product p ON sc.product_id=p.id
                LEFT JOIN branch b ON sc.branch_id=b.id
                WHERE sc.balance < %s {extra} ORDER BY sc.balance ASC""",
            params
        )


# ── Journal Entry Repository ──────────────────────────────────────

class JournalEntryRepository:
    """Double-entry journal management."""
    
    @staticmethod
    def create(
        doc_key: str,
        branch_id: str,
        entry_date: str,
        description: str = None,
        status: str = "draft",
        created_by: str = None,
    ) -> dict:
        return execute_returning(
            """INSERT INTO journal_entry (doc_key, branch_id, entry_date, description, status, total_debit, total_credit, created_by)
               VALUES (%s, %s, %s, %s, %s, 0, 0, %s) RETURNING *""",
            (doc_key, branch_id, entry_date, description, status, created_by)
        )
    
    @staticmethod
    def add_line(journal_entry_id: str, account_code: str, debit: float, credit: float, description: str = None) -> dict:
        return execute_returning(
            """INSERT INTO journal_entry_line (journal_entry_id, account_code, debit, credit, description)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (journal_entry_id, account_code, debit, credit, description)
        )
    
    @staticmethod
    def get(journal_entry_id: str) -> dict | None:
        je = fetch_one("SELECT * FROM journal_entry WHERE id = %s", (journal_entry_id,))
        if je:
            je["lines"] = fetch_all("SELECT * FROM journal_entry_line WHERE journal_entry_id = %s", (journal_entry_id,))
        return je
    
    @staticmethod
    def post(journal_entry_id: str) -> dict:
        """Post journal entry to General Ledger."""
        je = JournalEntryRepository.get(journal_entry_id)
        if not je:
            raise ValueError("Journal entry not found")
        if je["status"] == "posted":
            raise ValueError("Already posted")
        
        lines = je["lines"]
        total_debit = sum(float(l["debit"]) for l in lines)
        total_credit = sum(float(l["credit"]) for l in lines)
        
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(f"Debit ({total_debit}) must equal Credit ({total_credit})")
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Post to General Ledger
                for line in lines:
                    cur.execute(
                        """INSERT INTO general_ledger (doc_key, branch_id, account_code, debit, credit, balance, transaction_date, description)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (je["doc_key"], je["branch_id"], line["account_code"],
                         float(line["debit"]), float(line["credit"]),
                         float(line["debit"]) - float(line["credit"]),
                         je["entry_date"], line["description"])
                    )
                
                # Update journal entry status
                cur.execute(
                    "UPDATE journal_entry SET status='posted', total_debit=%s, total_credit=%s WHERE id=%s",
                    (total_debit, total_credit, journal_entry_id)
                )
        
        return JournalEntryRepository.get(journal_entry_id)
    
    @staticmethod
    def list_entries(branch_id: str = None, status: str = None, offset: int = 0, limit: int = 50) -> list[dict]:
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
        
        return fetch_all(
            f"""SELECT je.*, b.name as branch_name
                FROM journal_entry je
                LEFT JOIN branch b ON je.branch_id=b.id
                {where} ORDER BY je.entry_date DESC LIMIT %s OFFSET %s""",
            tuple(params)
        )


# ── General Ledger Repository ─────────────────────────────────────

class GeneralLedgerRepository:
    """General Ledger queries."""
    
    @staticmethod
    def get_entries(
        account_code: str = None,
        branch_id: str = None,
        date_from: str = None,
        date_to: str = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        conditions = []
        params = []
        if account_code:
            conditions.append("gl.account_code = %s")
            params.append(account_code)
        if branch_id:
            conditions.append("gl.branch_id = %s")
            params.append(branch_id)
        if date_from:
            conditions.append("gl.transaction_date >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("gl.transaction_date <= %s")
            params.append(date_to)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        
        return fetch_all(
            f"""SELECT gl.*, coa.account_name, coa.account_type
                FROM general_ledger gl
                JOIN chart_of_account coa ON gl.account_code=coa.account_code
                {where} ORDER BY gl.transaction_date DESC LIMIT %s OFFSET %s""",
            tuple(params)
        )
    
    @staticmethod
    def get_trial_balance(branch_id: str = None) -> dict:
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
    
    @staticmethod
    def get_profit_loss(branch_id: str = None) -> dict:
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
        
        result = {"revenue": 0, "cogs": 0, "operating_expenses": 0, "gross_profit": 0, "net_profit": 0}
        for r in rows:
            if r["account_type"] == "Revenue":
                result["revenue"] += float(r["total_credit"]) - float(r["total_debit"])
            elif r["account_type"] == "Expense":
                result["cogs"] += float(r["total_debit"]) - float(r["total_credit"])
        
        result["gross_profit"] = result["revenue"] - result["cogs"]
        result["net_profit"] = result["gross_profit"]
        return result


# ── Accounts Payable Repository ────────────────────────────────────

class AccountsPayableRepository:
    """Accounts Payable management."""
    
    @staticmethod
    def create(
        doc_key: str,
        supplier_name: str,
        amount: float,
        branch_id: str,
        invoice_no: str = None,
        invoice_date: str = None,
        due_date: str = None,
    ) -> dict:
        return execute_returning(
            """INSERT INTO accounts_payable (doc_key, supplier_name, invoice_no, invoice_date, due_date, amount, branch_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (doc_key, supplier_name, invoice_no, invoice_date, due_date, amount, branch_id)
        )
    
    @staticmethod
    def get(ap_id: str) -> dict | None:
        return fetch_one("SELECT * FROM accounts_payable WHERE id = %s", (ap_id,))
    
    @staticmethod
    def list_ap(status: str = None, branch_id: str = None, offset: int = 0, limit: int = 50) -> list[dict]:
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
        
        return fetch_all(
            f"""SELECT ap.*, b.name as branch_name
                FROM accounts_payable ap
                LEFT JOIN branch b ON ap.branch_id=b.id
                {where} ORDER BY ap.due_date LIMIT %s OFFSET %s""",
            tuple(params)
        )
    
    @staticmethod
    def record_payment(ap_id: str, amount: float, payment_date: str, payment_method_id: str = None, reference_no: str = None) -> dict:
        ap = AccountsPayableRepository.get(ap_id)
        if not ap:
            raise ValueError("AP not found")
        
        new_paid = float(ap["paid_amount"]) + amount
        status = "paid" if new_paid >= float(ap["amount"]) else "partial"
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ap_payment (ap_id, payment_date, amount, payment_method_id, reference_no) VALUES (%s, %s, %s, %s, %s)",
                    (ap_id, payment_date, amount, payment_method_id, reference_no)
                )
                cur.execute("UPDATE accounts_payable SET paid_amount=%s, status=%s WHERE id=%s", (new_paid, status, ap_id))
        
        return AccountsPayableRepository.get(ap_id)


# ── Bank Repository ───────────────────────────────────────────────

class BankRepository:
    """Bank account and transaction management."""
    
    @staticmethod
    def list_accounts(branch_id: str = None) -> list[dict]:
        if branch_id:
            return fetch_all(
                "SELECT ba.*, c.code as currency_code FROM bank_account ba LEFT JOIN currency c ON ba.currency_id=c.id WHERE ba.is_active=true AND ba.branch_id=%s",
                (branch_id,)
            )
        return fetch_all(
            "SELECT ba.*, c.code as currency_code, b.name as branch_name FROM bank_account ba LEFT JOIN currency c ON ba.currency_id=c.id LEFT JOIN branch b ON ba.branch_id=b.id WHERE ba.is_active=true"
        )
    
    @staticmethod
    def create_account(branch_id: str, bank_name: str, account_no: str, account_name: str = None, currency_id: str = None) -> dict:
        return execute_returning(
            "INSERT INTO bank_account (branch_id, bank_name, account_no, account_name, currency_id) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (branch_id, bank_name, account_no, account_name, currency_id)
        )
    
    @staticmethod
    def get_transactions(bank_account_id: str, offset: int = 0, limit: int = 50) -> list[dict]:
        return fetch_all(
            "SELECT * FROM bank_transaction WHERE bank_account_id=%s ORDER BY transaction_date DESC LIMIT %s OFFSET %s",
            (bank_account_id, limit, offset)
        )


# ── Daily Closing Repository ──────────────────────────────────────

class DailyClosingRepository:
    """POS daily closing management."""
    
    @staticmethod
    def create(branch_id: str, closing_date: str = None) -> dict:
        from pos_erp.routers.pos_router import generate_doc_key
        doc_key = generate_doc_key("CLO")
        closing_date = closing_date or date.today().isoformat()
        
        # Get all paid transactions for the day
        txns = fetch_all(
            """SELECT t.*, pm.type as payment_type FROM pos_transaction t
               LEFT JOIN payment_method pm ON t.payment_method_id = pm.id
               WHERE t.branch_id = %s AND t.status = 'paid' AND DATE(t.created_at) = %s""",
            (branch_id, closing_date)
        )
        
        total_cash = sum(float(t["total"]) for t in txns if t.get("payment_type") == "cash")
        total_card = sum(float(t["total"]) for t in txns if t.get("payment_type") == "card")
        total_transfer = sum(float(t["total"]) for t in txns if t.get("payment_type") == "bank_transfer")
        total_other = sum(float(t["total"]) for t in txns if t.get("payment_type") not in ("cash", "card", "bank_transfer"))
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO pos_daily_closing (doc_key, branch_id, closing_date, total_cash, total_card, total_transfer, total_other, total_transactions, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'draft') RETURNING *""",
                    (doc_key, branch_id, closing_date, total_cash, total_card, total_transfer, total_other, len(txns))
                )
                closing = cur.fetchone()
                
                for txn in txns:
                    cur.execute(
                        "INSERT INTO pos_daily_closing_detail (closing_id, transaction_id, amount) VALUES (%s, %s, %s)",
                        (closing["id"], txn["id"], txn["total"])
                    )
        
        return closing
    
    @staticmethod
    def get(closing_id: str) -> dict | None:
        closing = fetch_one("SELECT * FROM pos_daily_closing WHERE id = %s", (closing_id,))
        if closing:
            closing["details"] = fetch_all(
                "SELECT d.*, t.doc_key, t.customer_name FROM pos_daily_closing_detail d JOIN pos_transaction t ON d.transaction_id=t.id WHERE d.closing_id = %s",
                (closing_id,)
            )
        return closing
    
    @staticmethod
    def list_closings(branch_id: str = None, offset: int = 0, limit: int = 50) -> list[dict]:
        extra = "WHERE c.branch_id = %s" if branch_id else ""
        params = (branch_id,) if branch_id else ()
        return fetch_all(
            f"SELECT c.*, b.name as branch_name FROM pos_daily_closing c LEFT JOIN branch b ON c.branch_id=b.id {extra} ORDER BY c.closing_date DESC LIMIT %s OFFSET %s",
            (*params, limit, offset)
        )
    
    @staticmethod
    def submit(closing_id: str) -> dict:
        execute("UPDATE pos_daily_closing SET status='submitted' WHERE id = %s", (closing_id,))
        return DailyClosingRepository.get(closing_id)
