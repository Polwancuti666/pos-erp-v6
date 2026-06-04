#!/usr/bin/env python3
"""Migration: Add coa_id column to treatment_category and product_category."""
import sys
sys.path.insert(0, 'src')
from pos_erp.db import execute, fetch_all

print("Starting migration: add coa_id to category tables...")

# Add coa_id to treatment_category
execute("ALTER TABLE treatment_category ADD COLUMN IF NOT EXISTS coa_id UUID REFERENCES chart_of_account(id)")
print("  ✅ treatment_category.coa_id column added")

# Add coa_id to product_category
execute("ALTER TABLE product_category ADD COLUMN IF NOT EXISTS coa_id UUID REFERENCES chart_of_account(id)")
print("  ✅ product_category.coa_id column added")

# Verify
for table in ['treatment_category', 'product_category']:
    rows = fetch_all(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' ORDER BY ordinal_position")
    cols = [r['column_name'] for r in rows]
    has_coa = 'coa_id' in cols
    print(f"  {table}: coa_id={'✅' if has_coa else '❌'} columns={cols}")

print("\nMigration complete!")
