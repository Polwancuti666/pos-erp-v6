#!/usr/bin/env python3
"""Apply performance indexes to POS-ERP database."""
import sys
from pathlib import Path

# Add project src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pos_erp.db import execute, fetch_all

SQL_FILE = Path(__file__).parent / "src" / "pos_erp" / "migrations" / "performance_indexes.sql"


def main():
    if not SQL_FILE.exists():
        print(f"ERROR: {SQL_FILE} not found")
        sys.exit(1)

    sql = SQL_FILE.read_text()
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

    applied = 0
    errors = 0
    for stmt in statements:
        if not stmt:
            continue
        try:
            execute(stmt)
            applied += 1
            # Extract index name for logging
            if "CREATE INDEX" in stmt.upper():
                name = stmt.split("IF NOT EXISTS")[-1].split("ON")[0].strip() if "IF NOT EXISTS" in stmt.upper() else "unknown"
                print(f"  ✅ {name}")
        except Exception as e:
            errors += 1
            print(f"  ❌ {str(e)[:80]}")

    print(f"\nDone: {applied} applied, {errors} errors")


if __name__ == "__main__":
    main()
