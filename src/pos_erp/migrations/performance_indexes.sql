-- Performance Indexes for POS-ERP V6
-- Run: python apply_indexes.py

-- Transactions
CREATE INDEX IF NOT EXISTS idx_pos_txn_status_created ON pos_transaction(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pos_txn_branch_status ON pos_transaction(branch_id, status);
CREATE INDEX IF NOT EXISTS idx_pos_txn_customer ON pos_transaction(customer_name);
CREATE INDEX IF NOT EXISTS idx_pos_txn_doc_key ON pos_transaction(doc_key);

-- Transaction Items
CREATE INDEX IF NOT EXISTS idx_pos_txn_item_txn ON pos_transaction_item(transaction_id);
CREATE INDEX IF NOT EXISTS idx_pos_txn_item_type ON pos_transaction_item(item_type);

-- Treatment Records
CREATE INDEX IF NOT EXISTS idx_treatment_record_therapist ON treatment_record(therapist_id, status);
CREATE INDEX IF NOT EXISTS idx_treatment_record_txn ON treatment_record(transaction_id);
CREATE INDEX IF NOT EXISTS idx_treatment_record_time ON treatment_record(start_time DESC);

-- Stock
CREATE INDEX IF NOT EXISTS idx_stock_card_product_branch ON stock_card(product_id, branch_id);
CREATE INDEX IF NOT EXISTS idx_stock_card_balance ON stock_card(balance) WHERE balance < 10;
CREATE INDEX IF NOT EXISTS idx_stock_movement_product ON stock_movement(product_id, created_at DESC);

-- Staff Commission
CREATE INDEX IF NOT EXISTS idx_commission_therapist_status ON staff_commission(therapist_id, status);
CREATE INDEX IF NOT EXISTS idx_commission_created ON staff_commission(created_at DESC);

-- Loyalty
CREATE INDEX IF NOT EXISTS idx_loyalty_txn_customer ON loyalty_transaction(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customer_loyalty_tier ON customer(loyalty_tier) WHERE is_active = true;

-- Vouchers
CREATE INDEX IF NOT EXISTS idx_voucher_code ON voucher(code) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_voucher_dates ON voucher(valid_from, valid_until);

-- Sync Queue
CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status, created_at DESC);

-- Audit Trail
CREATE INDEX IF NOT EXISTS idx_audit_trail_doc ON audit_trail(doc_key, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trail_module ON audit_trail(module, timestamp DESC);

-- General Ledger
CREATE INDEX IF NOT EXISTS idx_gl_account ON general_ledger(account_code, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_gl_branch ON general_ledger(branch_id, transaction_date DESC);

-- AP
CREATE INDEX IF NOT EXISTS idx_ap_status ON accounts_payable(status) WHERE status IN ('open', 'partial');

-- Batch Expiry
CREATE INDEX IF NOT EXISTS idx_batch_expiry ON product_batch(expiry_date) WHERE qty > 0;
