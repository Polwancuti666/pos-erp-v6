-- ============================================================
-- Beauty & Shine ERP - Complete Database Schema
-- Based on BPMN v3 Specification
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. DOCUMENT REGISTRY & CROSS REFERENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS document_registry (
    doc_key VARCHAR(50) PRIMARY KEY,
    module VARCHAR(20) NOT NULL,
    branch_code VARCHAR(10) NOT NULL,
    doc_date DATE NOT NULL,
    sequence INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_cross_reference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc_key VARCHAR(50) REFERENCES document_registry(doc_key),
    target_doc_key VARCHAR(50) REFERENCES document_registry(doc_key),
    link_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_doc_registry_module ON document_registry(module);
CREATE INDEX idx_doc_registry_branch ON document_registry(branch_code);
CREATE INDEX idx_doc_xref_source ON document_cross_reference(source_doc_key);
CREATE INDEX idx_doc_xref_target ON document_cross_reference(target_doc_key);

-- ============================================================
-- 2. COMPANY & AUTH MASTER
-- ============================================================

CREATE TABLE IF NOT EXISTS company (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(100),
    logo_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS branch (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES company(id),
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS department (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branch(id),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS position (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID REFERENCES department(id),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS app_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    branch_id UUID REFERENCES branch(id),
    department_id UUID REFERENCES department(id),
    position_id UUID REFERENCES position(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_role (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES app_user(id),
    role_name VARCHAR(50) NOT NULL,
    branch_id UUID REFERENCES branch(id),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS role_permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,
    module VARCHAR(50) NOT NULL,
    can_create BOOLEAN DEFAULT FALSE,
    can_read BOOLEAN DEFAULT TRUE,
    can_update BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_approve BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS approval_flow (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module VARCHAR(50) NOT NULL,
    branch_id UUID REFERENCES branch(id),
    min_amount DECIMAL(15,2) DEFAULT 0,
    max_amount DECIMAL(15,2),
    approver_role VARCHAR(50) NOT NULL,
    sequence INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS approval_matrix (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) REFERENCES document_registry(doc_key),
    approver_user_id UUID REFERENCES app_user(id),
    status VARCHAR(20) DEFAULT 'pending',
    approved_at TIMESTAMP,
    notes TEXT
);

CREATE INDEX idx_user_branch ON app_user(branch_id);
CREATE INDEX idx_user_role_user ON user_role(user_id);
CREATE INDEX idx_approval_matrix_doc ON approval_matrix(doc_key);

-- ============================================================
-- 3. PRODUCT MASTER
-- ============================================================

CREATE TABLE IF NOT EXISTS product_category (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS product_subcategory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES product_category(id),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS product (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    category_id UUID REFERENCES product_category(id),
    subcategory_id UUID REFERENCES product_subcategory(id),
    unit VARCHAR(20) DEFAULT 'pcs',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_pricelist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES product(id),
    branch_id UUID REFERENCES branch(id),
    price DECIMAL(15,2) NOT NULL,
    effective_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS product_supplier (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES product(id),
    supplier_name VARCHAR(100) NOT NULL,
    supplier_code VARCHAR(50),
    lead_time_days INTEGER DEFAULT 0,
    min_order_qty INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS product_batch (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES product(id),
    branch_id UUID REFERENCES branch(id),
    batch_no VARCHAR(50) NOT NULL,
    expiry_date DATE,
    qty DECIMAL(15,2) DEFAULT 0,
    cost_per_unit DECIMAL(15,2) DEFAULT 0,
    received_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS product_account_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES product(id),
    account_code VARCHAR(20) NOT NULL,
    account_type VARCHAR(50),
    description TEXT
);

CREATE INDEX idx_product_sku ON product(sku);
CREATE INDEX idx_product_category ON product(category_id);
CREATE INDEX idx_pricelist_product ON product_pricelist(product_id);
CREATE INDEX idx_batch_product ON product_batch(product_id);

-- ============================================================
-- 4. POS MASTER
-- ============================================================

CREATE TABLE IF NOT EXISTS treatment_category (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS treatment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    category_id UUID REFERENCES treatment_category(id),
    duration_minutes INTEGER DEFAULT 60,
    price DECIMAL(15,2) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS treatment_package (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    total_sessions INTEGER DEFAULT 1,
    price DECIMAL(15,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS treatment_package_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID REFERENCES treatment_package(id),
    treatment_id UUID REFERENCES treatment(id),
    session_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bed_section (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branch(id),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS bed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID REFERENCES bed_section(id),
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'available',
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS voucher (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    min_purchase DECIMAL(15,2) DEFAULT 0,
    valid_from DATE,
    valid_until DATE,
    usage_limit INTEGER DEFAULT 1,
    used_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS promotion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    type VARCHAR(20) NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    applicable_to VARCHAR(50),
    valid_from DATE,
    valid_until DATE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS cancel_reason (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_treatment_category ON treatment(category_id);
CREATE INDEX idx_bed_section ON bed(section_id);

-- ============================================================
-- 5. ACCOUNTING MASTER
-- ============================================================

CREATE TABLE IF NOT EXISTS chart_of_account (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_code VARCHAR(20) UNIQUE NOT NULL,
    account_name VARCHAR(200) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    parent_code VARCHAR(20),
    level INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS currency (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    symbol VARCHAR(5),
    exchange_rate DECIMAL(15,4) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS tax_purpose (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    rate DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS payment_method (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS cash_flow_category (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS cost_center (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branch(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS financial_period (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branch(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    closed_by UUID REFERENCES app_user(id)
);

CREATE TABLE IF NOT EXISTS account_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    debit_account VARCHAR(20) NOT NULL,
    credit_account VARCHAR(20) NOT NULL,
    description TEXT
);

CREATE INDEX idx_coa_type ON chart_of_account(account_type);
CREATE INDEX idx_fin_period ON financial_period(branch_id, year, month);

-- ============================================================
-- 6. POS TRANSACTION
-- ============================================================

CREATE TABLE IF NOT EXISTS pos_transaction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    branch_id UUID REFERENCES branch(id),
    customer_name VARCHAR(100),
    customer_phone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'open',
    subtotal DECIMAL(15,2) DEFAULT 0,
    discount DECIMAL(15,2) DEFAULT 0,
    tax DECIMAL(15,2) DEFAULT 0,
    total DECIMAL(15,2) DEFAULT 0,
    payment_method_id UUID REFERENCES payment_method(id),
    cashier_id UUID REFERENCES app_user(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pos_transaction_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES pos_transaction(id),
    item_type VARCHAR(20) NOT NULL,
    item_id UUID,
    item_name VARCHAR(200),
    qty DECIMAL(15,2) DEFAULT 1,
    unit_price DECIMAL(15,2) DEFAULT 0,
    discount DECIMAL(15,2) DEFAULT 0,
    total DECIMAL(15,2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pos_daily_closing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    branch_id UUID REFERENCES branch(id),
    closing_date DATE NOT NULL,
    total_cash DECIMAL(15,2) DEFAULT 0,
    total_card DECIMAL(15,2) DEFAULT 0,
    total_transfer DECIMAL(15,2) DEFAULT 0,
    total_other DECIMAL(15,2) DEFAULT 0,
    total_transactions INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    closed_by UUID REFERENCES app_user(id),
    closed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pos_daily_closing_detail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    closing_id UUID REFERENCES pos_daily_closing(id),
    transaction_id UUID REFERENCES pos_transaction(id),
    amount DECIMAL(15,2) DEFAULT 0
);

CREATE INDEX idx_pos_txn_branch ON pos_transaction(branch_id);
CREATE INDEX idx_pos_txn_status ON pos_transaction(status);
CREATE INDEX idx_pos_txn_date ON pos_transaction(created_at);
CREATE INDEX idx_pos_closing_date ON pos_daily_closing(closing_date);

-- ============================================================
-- 7. TREATMENT RECORDS
-- ============================================================

CREATE TABLE IF NOT EXISTS treatment_record (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    transaction_id UUID REFERENCES pos_transaction(id),
    treatment_id UUID REFERENCES treatment(id),
    therapist_id UUID REFERENCES app_user(id),
    bed_id UUID REFERENCES bed(id),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'scheduled',
    notes TEXT,
    consent_signed BOOLEAN DEFAULT FALSE,
    before_photo_url TEXT,
    after_photo_url TEXT
);

CREATE INDEX idx_treatment_record_txn ON treatment_record(transaction_id);
CREATE INDEX idx_treatment_record_therapist ON treatment_record(therapist_id);

-- ============================================================
-- 8. INVENTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS stock_card (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES product(id),
    branch_id UUID REFERENCES branch(id),
    qty_in DECIMAL(15,2) DEFAULT 0,
    qty_out DECIMAL(15,2) DEFAULT 0,
    balance DECIMAL(15,2) DEFAULT 0,
    last_movement_date DATE
);

CREATE TABLE IF NOT EXISTS stock_movement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) REFERENCES document_registry(doc_key),
    product_id UUID REFERENCES product(id),
    batch_id UUID REFERENCES product_batch(id),
    branch_id UUID REFERENCES branch(id),
    movement_type VARCHAR(20) NOT NULL,
    qty DECIMAL(15,2) NOT NULL,
    reference_doc_key VARCHAR(50),
    notes TEXT,
    created_by UUID REFERENCES app_user(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_opname (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    branch_id UUID REFERENCES branch(id),
    opname_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    notes TEXT,
    created_by UUID REFERENCES app_user(id),
    approved_by UUID REFERENCES app_user(id)
);

CREATE TABLE IF NOT EXISTS stock_opname_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opname_id UUID REFERENCES stock_opname(id),
    product_id UUID REFERENCES product(id),
    system_qty DECIMAL(15,2) DEFAULT 0,
    actual_qty DECIMAL(15,2) DEFAULT 0,
    difference DECIMAL(15,2) DEFAULT 0,
    notes TEXT
);

CREATE INDEX idx_stock_card_product ON stock_card(product_id);
CREATE INDEX idx_stock_movement_product ON stock_movement(product_id);
CREATE INDEX idx_stock_movement_doc ON stock_movement(doc_key);

-- ============================================================
-- 9. WIP & BOM
-- ============================================================

CREATE TABLE IF NOT EXISTS bom_header (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES product(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    standard_cost DECIMAL(15,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS bom_component (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bom_id UUID REFERENCES bom_header(id),
    component_product_id UUID REFERENCES product(id),
    qty DECIMAL(15,4) NOT NULL,
    unit VARCHAR(20),
    cost_per_unit DECIMAL(15,2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS wip_order (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    branch_id UUID REFERENCES branch(id),
    product_id UUID REFERENCES product(id),
    bom_id UUID REFERENCES bom_header(id),
    planned_qty DECIMAL(15,2) NOT NULL,
    actual_qty DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'planned',
    start_date DATE,
    end_date DATE,
    created_by UUID REFERENCES app_user(id)
);

CREATE TABLE IF NOT EXISTS wip_consumption (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wip_order_id UUID REFERENCES wip_order(id),
    component_product_id UUID REFERENCES product(id),
    planned_qty DECIMAL(15,2) DEFAULT 0,
    actual_qty DECIMAL(15,2) DEFAULT 0,
    variance DECIMAL(15,2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS wip_output (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wip_order_id UUID REFERENCES wip_order(id),
    product_id UUID REFERENCES product(id),
    qty DECIMAL(15,2) DEFAULT 0,
    qc_status VARCHAR(20) DEFAULT 'pending',
    notes TEXT
);

CREATE INDEX idx_bom_product ON bom_header(product_id);
CREATE INDEX idx_wip_order_branch ON wip_order(branch_id);

-- ============================================================
-- 10. FINANCE
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts_payable (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    supplier_name VARCHAR(100) NOT NULL,
    invoice_no VARCHAR(50),
    invoice_date DATE,
    due_date DATE,
    amount DECIMAL(15,2) NOT NULL,
    paid_amount DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'open',
    branch_id UUID REFERENCES branch(id)
);

CREATE TABLE IF NOT EXISTS ap_payment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ap_id UUID REFERENCES accounts_payable(id),
    payment_date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    payment_method_id UUID REFERENCES payment_method(id),
    reference_no VARCHAR(50),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS general_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) REFERENCES document_registry(doc_key),
    branch_id UUID REFERENCES branch(id),
    account_code VARCHAR(20) NOT NULL,
    debit DECIMAL(15,2) DEFAULT 0,
    credit DECIMAL(15,2) DEFAULT 0,
    balance DECIMAL(15,2) DEFAULT 0,
    transaction_date DATE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bank_account (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branch(id),
    bank_name VARCHAR(100) NOT NULL,
    account_no VARCHAR(50) NOT NULL,
    account_name VARCHAR(100),
    currency_id UUID REFERENCES currency(id),
    balance DECIMAL(15,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS bank_transaction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id UUID REFERENCES bank_account(id),
    transaction_date DATE NOT NULL,
    description TEXT,
    debit DECIMAL(15,2) DEFAULT 0,
    credit DECIMAL(15,2) DEFAULT 0,
    balance DECIMAL(15,2) DEFAULT 0,
    reference_doc_key VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS bank_reconciliation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id UUID REFERENCES bank_account(id),
    period VARCHAR(20) NOT NULL,
    statement_balance DECIMAL(15,2) DEFAULT 0,
    book_balance DECIMAL(15,2) DEFAULT 0,
    difference DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    reconciled_by UUID REFERENCES app_user(id),
    reconciled_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bank_reconciliation_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID REFERENCES bank_reconciliation(id),
    type VARCHAR(20) NOT NULL,
    description TEXT,
    amount DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'unmatched'
);

CREATE TABLE IF NOT EXISTS journal_entry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    branch_id UUID REFERENCES branch(id),
    entry_date DATE NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    total_debit DECIMAL(15,2) DEFAULT 0,
    total_credit DECIMAL(15,2) DEFAULT 0,
    created_by UUID REFERENCES app_user(id),
    approved_by UUID REFERENCES app_user(id)
);

CREATE TABLE IF NOT EXISTS journal_entry_line (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_entry_id UUID REFERENCES journal_entry(id),
    account_code VARCHAR(20) NOT NULL,
    debit DECIMAL(15,2) DEFAULT 0,
    credit DECIMAL(15,2) DEFAULT 0,
    description TEXT
);

CREATE TABLE IF NOT EXISTS profit_loss (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branch(id),
    period VARCHAR(20) NOT NULL,
    revenue DECIMAL(15,2) DEFAULT 0,
    cogs DECIMAL(15,2) DEFAULT 0,
    gross_profit DECIMAL(15,2) DEFAULT 0,
    operating_expenses DECIMAL(15,2) DEFAULT 0,
    net_profit DECIMAL(15,2) DEFAULT 0,
    generated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gl_account ON general_ledger(account_code);
CREATE INDEX idx_gl_date ON general_ledger(transaction_date);
CREATE INDEX idx_gl_doc ON general_ledger(doc_key);
CREATE INDEX idx_ap_status ON accounts_payable(status);
CREATE INDEX idx_je_status ON journal_entry(status);

-- ============================================================
-- 11. ASSET MANAGEMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS asset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50) UNIQUE REFERENCES document_registry(doc_key),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    purchase_date DATE,
    purchase_cost DECIMAL(15,2) DEFAULT 0,
    salvage_value DECIMAL(15,2) DEFAULT 0,
    useful_life_months INTEGER DEFAULT 0,
    depreciation_method VARCHAR(20) DEFAULT 'straight_line',
    branch_id UUID REFERENCES branch(id),
    status VARCHAR(20) DEFAULT 'active',
    current_value DECIMAL(15,2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS asset_depreciation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES asset(id),
    period VARCHAR(20) NOT NULL,
    depreciation_amount DECIMAL(15,2) DEFAULT 0,
    accumulated_depreciation DECIMAL(15,2) DEFAULT 0,
    book_value DECIMAL(15,2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS asset_maintenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES asset(id),
    maintenance_date DATE NOT NULL,
    description TEXT,
    cost DECIMAL(15,2) DEFAULT 0,
    next_maintenance_date DATE
);

CREATE TABLE IF NOT EXISTS asset_disposal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES asset(id),
    disposal_date DATE NOT NULL,
    disposal_value DECIMAL(15,2) DEFAULT 0,
    gain_loss DECIMAL(15,2) DEFAULT 0,
    reason TEXT,
    approved_by UUID REFERENCES app_user(id)
);

CREATE INDEX idx_asset_branch ON asset(branch_id);
CREATE INDEX idx_asset_status ON asset(status);

-- ============================================================
-- 12. END OF PERIOD & AUDIT
-- ============================================================

CREATE TABLE IF NOT EXISTS period_closing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branch(id),
    period VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    reviewed_by UUID REFERENCES app_user(id),
    reviewed_at TIMESTAMP,
    closed_by UUID REFERENCES app_user(id),
    closed_at TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS period_closing_checklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    closing_id UUID REFERENCES period_closing(id),
    check_name VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    checked_by UUID REFERENCES app_user(id),
    checked_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50),
    module VARCHAR(50),
    action VARCHAR(20) NOT NULL,
    user_id UUID,
    user_name VARCHAR(100),
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attachment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key VARCHAR(50),
    file_name VARCHAR(200) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    uploaded_by UUID REFERENCES app_user(id),
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_doc ON audit_trail(doc_key);
CREATE INDEX idx_audit_module ON audit_trail(module);
CREATE INDEX idx_audit_timestamp ON audit_trail(timestamp);

-- ============================================================
-- 13. SYNC & INTEGRATION
-- ============================================================

CREATE TABLE IF NOT EXISTS sync_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,
    target VARCHAR(50) NOT NULL,
    doc_key VARCHAR(50),
    payload JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS integration_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50),
    target VARCHAR(50),
    doc_key VARCHAR(50),
    request_payload JSONB,
    response_payload JSONB,
    status VARCHAR(20),
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sync_status ON sync_queue(status);
CREATE INDEX idx_sync_doc ON sync_queue(doc_key);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Company
INSERT INTO company (name, address, phone, email) VALUES
('Beauty & Shine', 'BSD City, Tangerang Selatan', '021-12345678', 'info@beautynshine.web.id')
ON CONFLICT DO NOTHING;

-- Branch
DO $$
DECLARE company_id UUID;
BEGIN
    SELECT id INTO company_id FROM company LIMIT 1;
    INSERT INTO branch (company_id, code, name, address, phone) VALUES
    (company_id, 'BSD', 'Beauty & Shine BSD', 'BSD City, Tangerang Selatan', '021-12345678')
    ON CONFLICT (code) DO NOTHING;
END $$;

-- Department
DO $$
DECLARE branch_id UUID;
BEGIN
    SELECT id INTO branch_id FROM branch WHERE code = 'BSD';
    INSERT INTO department (branch_id, name) VALUES
    (branch_id, 'Management'),
    (branch_id, 'Kasir'),
    (branch_id, 'Therapist'),
    (branch_id, 'Finance')
    ON CONFLICT DO NOTHING;
END $$;

-- Position
DO $$
DECLARE dept_id UUID;
BEGIN
    SELECT id INTO dept_id FROM department WHERE name = 'Management' LIMIT 1;
    INSERT INTO position (department_id, name) VALUES (dept_id, 'Owner'), (dept_id, 'Manager')
    ON CONFLICT DO NOTHING;
    SELECT id INTO dept_id FROM department WHERE name = 'Kasir' LIMIT 1;
    INSERT INTO position (department_id, name) VALUES (dept_id, 'Kasir')
    ON CONFLICT DO NOTHING;
    SELECT id INTO dept_id FROM department WHERE name = 'Therapist' LIMIT 1;
    INSERT INTO position (department_id, name) VALUES (dept_id, 'Therapist Senior'), (dept_id, 'Therapist Junior')
    ON CONFLICT DO NOTHING;
END $$;

-- Users (admin & kasir)
DO $$
DECLARE branch_id UUID; dept_mgmt UUID; dept_kasir UUID; pos_owner UUID; pos_kasir UUID;
BEGIN
    SELECT id INTO branch_id FROM branch WHERE code = 'BSD';
    SELECT id INTO dept_mgmt FROM department WHERE name = 'Management' LIMIT 1;
    SELECT id INTO dept_kasir FROM department WHERE name = 'Kasir' LIMIT 1;
    SELECT id INTO pos_owner FROM position WHERE name = 'Owner' LIMIT 1;
    SELECT id INTO pos_kasir FROM position WHERE name = 'Kasir' LIMIT 1;

    INSERT INTO app_user (username, password_hash, full_name, branch_id, department_id, position_id) VALUES
    ('admin', 'admin123', 'Administrator', branch_id, dept_mgmt, pos_owner),
    ('kasir', 'kasir123', 'Kasir Utama', branch_id, dept_kasir, pos_kasir)
    ON CONFLICT (username) DO NOTHING;

    -- Roles
    INSERT INTO user_role (user_id, role_name, branch_id)
    SELECT id, 'admin', branch_id FROM app_user WHERE username = 'admin'
    ON CONFLICT DO NOTHING;
    INSERT INTO user_role (user_id, role_name, branch_id)
    SELECT id, 'kasir', branch_id FROM app_user WHERE username = 'kasir'
    ON CONFLICT DO NOTHING;
END $$;

-- Role Permissions
INSERT INTO role_permission (role_name, module, can_create, can_read, can_update, can_delete, can_approve) VALUES
('admin', 'pos', true, true, true, true, true),
('admin', 'inventory', true, true, true, true, true),
('admin', 'finance', true, true, true, true, true),
('admin', 'reporting', true, true, true, true, true),
('admin', 'master', true, true, true, true, true),
('kasir', 'pos', true, true, true, false, false),
('kasir', 'inventory', false, true, false, false, false)
ON CONFLICT DO NOTHING;

-- Chart of Accounts
INSERT INTO chart_of_account (account_code, account_name, account_type, level) VALUES
('1000', 'Kas & Bank', 'Asset', 1),
('1001', 'Kas', 'Asset', 2),
('1002', 'Bank BCA', 'Asset', 2),
('1003', 'Bank Mandiri', 'Asset', 2),
('1100', 'Piutang Usaha', 'Asset', 1),
('1200', 'Persediaan', 'Asset', 1),
('1300', 'Aset Tetap', 'Asset', 1),
('1301', 'Aset Tetap - Akumulasi Penyusutan', 'Asset', 2),
('2000', 'Hutang Usaha', 'Liability', 1),
('2100', 'Hutang Pajak', 'Liability', 1),
('3000', 'Modal', 'Equity', 1),
('3100', 'Laba Ditahan', 'Equity', 1),
('4000', 'Pendapatan', 'Revenue', 1),
('4001', 'Pendapatan Treatment', 'Revenue', 2),
('4002', 'Pendapatan Produk', 'Revenue', 2),
('5000', 'Harga Pokok Penjualan', 'Expense', 1),
('5001', 'HPP Treatment', 'Expense', 2),
('5002', 'HPP Produk', 'Expense', 2),
('6000', 'Biaya Operasional', 'Expense', 1),
('6001', 'Gaji Karyawan', 'Expense', 2),
('6002', 'Sewa', 'Expense', 2),
('6003', 'Utilitas', 'Expense', 2),
('6004', 'Marketing', 'Expense', 2),
('7000', 'Pendapatan Lain-lain', 'Revenue', 1),
('8000', 'Biaya Lain-lain', 'Expense', 1)
ON CONFLICT (account_code) DO NOTHING;

-- Currency
INSERT INTO currency (code, name, symbol, exchange_rate) VALUES
('IDR', 'Indonesian Rupiah', 'Rp', 1.0),
('USD', 'US Dollar', '$', 15500.0)
ON CONFLICT (code) DO NOTHING;

-- Payment Methods
INSERT INTO payment_method (name, type) VALUES
('Tunai', 'cash'),
('BCA', 'bank_transfer'),
('Mandiri', 'bank_transfer'),
('GoPay', 'e_wallet'),
('OVO', 'e_wallet'),
('QRIS', 'qris'),
('Kartu Kredit', 'card'),
('Kartu Debit', 'card')
ON CONFLICT DO NOTHING;

-- Tax Purpose
INSERT INTO tax_purpose (name, rate) VALUES
('PPN', 11.0),
('PPh 23', 2.0),
('Non-Tax', 0.0)
ON CONFLICT DO NOTHING;

-- Cash Flow Category
INSERT INTO cash_flow_category (name, type) VALUES
('Pendapatan Operasional', 'operating'),
('Biaya Operasional', 'operating'),
('Investasi Aset', 'investing'),
('Pendanaan', 'financing')
ON CONFLICT DO NOTHING;

-- Financial Periods (Jan-May 2026)
DO $$
DECLARE branch_id UUID;
BEGIN
    SELECT id INTO branch_id FROM branch WHERE code = 'BSD';
    INSERT INTO financial_period (branch_id, year, month, status) VALUES
    (branch_id, 2026, 1, 'open'),
    (branch_id, 2026, 2, 'open'),
    (branch_id, 2026, 3, 'open'),
    (branch_id, 2026, 4, 'open'),
    (branch_id, 2026, 5, 'open')
    ON CONFLICT DO NOTHING;
END $$;

-- Product Categories
INSERT INTO product_category (name) VALUES
('Skincare'), ('Haircare'), ('Bodycare'), ('Tools & Equipment')
ON CONFLICT DO NOTHING;

-- Product Subcategories
DO $$
DECLARE cat_id UUID;
BEGIN
    SELECT id INTO cat_id FROM product_category WHERE name = 'Skincare';
    INSERT INTO product_subcategory (category_id, name) VALUES
    (cat_id, 'Cleanser'), (cat_id, 'Moisturizer'), (cat_id, 'Serum'), (cat_id, 'Sunscreen')
    ON CONFLICT DO NOTHING;
    SELECT id INTO cat_id FROM product_category WHERE name = 'Haircare';
    INSERT INTO product_subcategory (category_id, name) VALUES
    (cat_id, 'Shampoo'), (cat_id, 'Conditioner'), (cat_id, 'Hair Mask')
    ON CONFLICT DO NOTHING;
    SELECT id INTO cat_id FROM product_category WHERE name = 'Bodycare';
    INSERT INTO product_subcategory (category_id, name) VALUES
    (cat_id, 'Body Lotion'), (cat_id, 'Body Scrub')
    ON CONFLICT DO NOTHING;
END $$;

-- Treatment Categories
INSERT INTO treatment_category (name) VALUES
('Facial'), ('Body'), ('Hair'), ('Nail')
ON CONFLICT DO NOTHING;

-- Treatments
DO $$
DECLARE cat_id UUID;
BEGIN
    SELECT id INTO cat_id FROM treatment_category WHERE name = 'Facial';
    INSERT INTO treatment (name, category_id, duration_minutes, price, description) VALUES
    ('Basic Facial', cat_id, 60, 150000, 'Facial dasar untuk perawatan kulit'),
    ('Premium Facial', cat_id, 90, 350000, 'Facial premium dengan serum & masker'),
    ('Acne Treatment', cat_id, 75, 250000, 'Perawatan khusus kulit berjerawat')
    ON CONFLICT DO NOTHING;
    SELECT id INTO cat_id FROM treatment_category WHERE name = 'Body';
    INSERT INTO treatment (name, category_id, duration_minutes, price, description) VALUES
    ('Body Massage', cat_id, 90, 200000, 'Pijat seluruh tubuh'),
    ('Body Scrub', cat_id, 60, 175000, 'Scrub tubuh untuk eksfoliasi'),
    ('Body Wrap', cat_id, 75, 300000, 'Body wrap untuk detoksifikasi')
    ON CONFLICT DO NOTHING;
    SELECT id INTO cat_id FROM treatment_category WHERE name = 'Hair';
    INSERT INTO treatment (name, category_id, duration_minutes, price, description) VALUES
    ('Hair Spa', cat_id, 60, 150000, 'Perawatan rambut dengan spa'),
    ('Hair Mask', cat_id, 45, 100000, 'Masker rambut untuk nutrisi')
    ON CONFLICT DO NOTHING;
    SELECT id INTO cat_id FROM treatment_category WHERE name = 'Nail';
    INSERT INTO treatment (name, category_id, duration_minutes, price, description) VALUES
    ('Manicure', cat_id, 45, 75000, 'Perawatan kuku tangan'),
    ('Pedicure', cat_id, 60, 100000, 'Perawatan kuku kaki'),
    ('Gel Nails', cat_id, 90, 200000, 'Kutek gel tahan lama')
    ON CONFLICT DO NOTHING;
END $$;

-- Bed Sections & Beds
DO $$
DECLARE branch_id UUID; section_id UUID;
BEGIN
    SELECT id INTO branch_id FROM branch WHERE code = 'BSD';

    INSERT INTO bed_section (branch_id, name) VALUES (branch_id, 'VIP Room') RETURNING id INTO section_id;
    INSERT INTO bed (section_id, name) VALUES (section_id, 'VIP-1'), (section_id, 'VIP-2');

    INSERT INTO bed_section (branch_id, name) VALUES (branch_id, 'Regular Room') RETURNING id INTO section_id;
    INSERT INTO bed (section_id, name) VALUES (section_id, 'REG-1'), (section_id, 'REG-2');

    INSERT INTO bed_section (branch_id, name) VALUES (branch_id, 'Hair Studio') RETURNING id INTO section_id;
    INSERT INTO bed (section_id, name) VALUES (section_id, 'HAIR-1'), (section_id, 'HAIR-2');
END $$;

-- Cancel Reasons
INSERT INTO cancel_reason (module, reason) VALUES
('pos', 'Customer batal'),
('pos', 'Stok habis'),
('pos', 'Customer komplain'),
('pos', 'Kesalahan input'),
('pos', 'Lainnya')
ON CONFLICT DO NOTHING;

-- Default Account Mapping
INSERT INTO account_mapping (module, transaction_type, debit_account, credit_account, description) VALUES
('pos', 'sale_cash', '1001', '4001', 'Penjualan treatment tunai'),
('pos', 'sale_bank', '1002', '4001', 'Penjualan treatment bank'),
('pos', 'sale_product', '1001', '4002', 'Penjualan produk'),
('inventory', 'stock_in', '1200', '2000', 'Penerimaan stok'),
('inventory', 'stock_out', '5000', '1200', 'Pengeluaran stok (COGS)'),
('finance', 'expense', '6000', '1001', 'Biaya operasional'),
('finance', 'salary', '6001', '1001', 'Gaji karyawan')
ON CONFLICT DO NOTHING;

-- Document Sequences (initial)
INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence, status) VALUES
('SEQ-BOOK-BSD-2026', 'BOOK', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-POS-BSD-2026', 'POS', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-TRM-BSD-2026', 'TRM', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-STK-BSD-2026', 'STK', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-WIP-BSD-2026', 'WIP', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-AP-BSD-2026', 'AP', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-JE-BSD-2026', 'JE', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-FA-BSD-2026', 'FA', 'BSD', '2026-01-01', 0, 'system'),
('SEQ-EOP-BSD-2026', 'EOP', 'BSD', '2026-01-01', 0, 'system')
ON CONFLICT (doc_key) DO NOTHING;

-- Bank Account
DO $$
DECLARE branch_id UUID; curr_id UUID;
BEGIN
    SELECT id INTO branch_id FROM branch WHERE code = 'BSD';
    SELECT id INTO curr_id FROM currency WHERE code = 'IDR';
    INSERT INTO bank_account (branch_id, bank_name, account_no, account_name, currency_id, balance) VALUES
    (branch_id, 'BCA', '1234567890', 'Beauty & Shine BSD', curr_id, 0),
    (branch_id, 'Mandiri', '0987654321', 'Beauty & Shine BSD', curr_id, 0)
    ON CONFLICT DO NOTHING;
END $$;

-- Cost Center
DO $$
DECLARE branch_id UUID;
BEGIN
    SELECT id INTO branch_id FROM branch WHERE code = 'BSD';
    INSERT INTO cost_center (branch_id, name, code) VALUES
    (branch_id, 'Operasional', 'OPS'),
    (branch_id, 'Marketing', 'MKT'),
    (branch_id, 'Administrasi', 'ADM')
    ON CONFLICT DO NOTHING;
END $$;

-- Approval Flow
DO $$
DECLARE branch_id UUID;
BEGIN
    SELECT id INTO branch_id FROM branch WHERE code = 'BSD';
    INSERT INTO approval_flow (module, branch_id, min_amount, max_amount, approver_role, sequence) VALUES
    ('pos', branch_id, 0, 1000000, 'kasir', 1),
    ('pos', branch_id, 1000001, 999999999, 'admin', 1),
    ('finance', branch_id, 0, 5000000, 'admin', 1),
    ('finance', branch_id, 5000001, 999999999, 'owner', 1)
    ON CONFLICT DO NOTHING;
END $$;

SELECT 'Schema created and seeded successfully!' as status;
