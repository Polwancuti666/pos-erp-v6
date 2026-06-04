# 02 — Database Migration

Complete guide for migrating the SQLite database to the new VPS.

## Overview

The ERP uses SQLite as its primary database. This guide covers:

1. Backing up the current database
2. Transferring to the new server
3. Restoring and verifying

---

## Step 1: Backup Current Database

### On the OLD server:

```bash
# Navigate to project directory
cd /var/www/pos-erp-v6

# Stop the application
sudo systemctl stop pos-erp

# Create backup directory
mkdir -p /var/www/pos-erp-v6/backups/migration

# Backup database with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp pos_erp.db /var/www/pos-erp-v6/backups/migration/pos_erp_${TIMESTAMP}.db

# Verify backup integrity
sqlite3 /var/www/pos-erp-v6/backups/migration/pos_erp_${TIMESTAMP}.db "PRAGMA integrity_check;"

# Get database stats
echo "=== Database Stats ==="
sqlite3 /var/www/pos-erp-v6/backups/migration/pos_erp_${TIMESTAMP}.db "
  SELECT 'Branches: ' || COUNT(*) FROM branch;
  SELECT 'Users: ' || COUNT(*) FROM users;
  SELECT 'Products: ' || COUNT(*) FROM product;
  SELECT 'Transactions: ' || COUNT(*) FROM txn;
  SELECT 'Inventory: ' || COUNT(*) FROM inventory_move;
"

# Create compressed backup
tar czf /var/www/pos-erp-v6/backups/migration/pos_erp_${TIMESTAMP}.tar.gz \
  -C /var/www/pos-erp-v6/backups/migration \
  pos_erp_${TIMESTAMP}.db

# Backup .env file
cp /var/www/pos-erp-v6/.env /var/www/pos-erp-v6/backups/migration/env_backup_${TIMESTAMP}

echo "Backup created: pos_erp_${TIMESTAMP}.tar.gz"
ls -lh /var/www/pos-erp-v6/backups/migration/
```

---

## Step 2: Transfer to New Server

### Option A: SCP (Recommended)

```bash
# From OLD server, transfer to new server
scp /var/www/pos-erp-v6/backups/migration/pos_erp_${TIMESTAMP}.tar.gz \
  deploy@NEW_VPS_IP:/var/www/pos-erp-v6/backups/

# Transfer .env file
scp /var/www/pos-erp-v6/backups/migration/env_backup_${TIMESTAMP} \
  deploy@NEW_VPS_IP:/var/www/pos-erp-v6/.env
```

### Option B: rsync (For large databases)

```bash
# From OLD server
rsync -avz --progress \
  /var/www/pos-erp-v6/backups/migration/pos_erp_${TIMESTAMP}.tar.gz \
  deploy@NEW_VPS_IP:/var/www/pos-erp-v6/backups/
```

### Option C: Via local machine (If no direct SSH between servers)

```bash
# On LOCAL machine
# 1. Download from old server
scp deploy@OLD_VPS_IP:/var/www/pos-erp-v6/backups/migration/pos_erp_${TIMESTAMP}.tar.gz \
  /tmp/

# 2. Upload to new server
scp /tmp/pos_erp_${TIMESTAMP}.tar.gz \
  deploy@NEW_VPS_IP:/var/www/pos-erp-v6/backups/

# 3. Transfer .env
scp deploy@OLD_VPS_IP:/var/www/pos-erp-v6/.env \
  /tmp/env_backup

scp /tmp/env_backup \
  deploy@NEW_VPS_IP:/var/www/pos-erp-v6/.env

# 4. Cleanup
rm /tmp/pos_erp_${TIMESTAMP}.tar.gz /tmp/env_backup
```

---

## Step 3: Restore on New Server

### On the NEW server:

```bash
# Navigate to project directory
cd /var/www/pos-erp-v6

# Extract backup
tar xzf backups/pos_erp_${TIMESTAMP}.tar.gz -C backups/

# Move database to correct location
mv backups/pos_erp_${TIMESTAMP}.db pos_erp.db

# Set permissions
chmod 664 pos_erp.db
chown deploy:deploy pos_erp.db

# Verify database integrity
sqlite3 pos_erp.db "PRAGMA integrity_check;"

# Check database stats
echo "=== Database Stats ==="
sqlite3 pos_erp.db "
  SELECT 'Branches: ' || COUNT(*) FROM branch;
  SELECT 'Users: ' || COUNT(*) FROM users;
  SELECT 'Products: ' || COUNT(*) FROM product;
  SELECT 'Transactions: ' || COUNT(*) FROM txn;
  SELECT 'Inventory: ' || COUNT(*) FROM inventory_move;
"

# Verify schema version
sqlite3 pos_erp.db "SELECT * FROM schema_version ORDER BY version DESC LIMIT 5;"
```

---

## Step 4: Run Migrations (If Needed)

```bash
# Navigate to project directory
cd /var/www/pos-erp-v6

# Activate virtual environment
source .venv/bin/activate

# Run any pending migrations
python scripts/migrate_category_coa.py

# Apply performance indexes
sqlite3 pos_erp.db < src/pos_erp/migrations/performance_indexes.sql

# Verify indexes
sqlite3 pos_erp.db ".indexes"
```

---

## Step 5: Verify Data Integrity

```bash
# Create verification script
cat > /tmp/verify_migration.sh << 'SCRIPT'
#!/bin/bash
echo "=== Database Migration Verification ==="
echo ""

DB="/var/www/pos-erp-v6/pos_erp.db"

# Check integrity
echo "1. Integrity Check:"
INTEGRITY=$(sqlite3 "$DB" "PRAGMA integrity_check;")
if [ "$INTEGRITY" = "ok" ]; then
    echo "   ✓ Database integrity: OK"
else
    echo "   ✗ Database integrity: FAILED"
    echo "   $INTEGRITY"
    exit 1
fi

# Check tables exist
echo ""
echo "2. Table Verification:"
TABLES=$(sqlite3 "$DB" ".tables")
REQUIRED_TABLES="branch users product txn inventory_move journal account"

for table in $REQUIRED_TABLES; do
    if echo "$TABLES" | grep -q "$table"; then
        COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM $table;")
        echo "   ✓ $table: $COUNT records"
    else
        echo "   ✗ $table: MISSING"
    fi
done

# Check foreign keys
echo ""
echo "3. Foreign Key Check:"
FK_ERRORS=$(sqlite3 "$DB" "PRAGMA foreign_key_check;" | wc -l)
if [ "$FK_ERRORS" -eq 0 ]; then
    echo "   ✓ Foreign keys: OK"
else
    echo "   ✗ Foreign keys: $FK_ERRORS errors"
fi

# Check indexes
echo ""
echo "4. Index Check:"
INDEX_COUNT=$(sqlite3 "$DB" ".indexes" | wc -l)
echo "   ✓ Indexes: $INDEX_COUNT"

# Check database size
echo ""
echo "5. Database Size:"
ls -lh "$DB" | awk '{print "   ✓ Size:", $5}'

echo ""
echo "=== Verification Complete ==="
SCRIPT

chmod +x /tmp/verify_migration.sh
/tmp/verify_migration.sh
```

---

## Step 6: Test Application Connection

```bash
# Start the application
sudo systemctl start pos-erp

# Wait for startup
sleep 3

# Test API endpoint
curl -s http://localhost:8000/health | jq .

# Test database connection
curl -s http://localhost:8000/api/v1/branches | jq .

# Check logs for errors
sudo journalctl -u pos-erp --since "1 minute ago" | grep -i error
```

---

## Troubleshooting

### Database Locked Error
```bash
# Check if another process is using the database
lsof pos_erp.db

# Kill any hanging processes
kill -9 <PID>
```

### Schema Mismatch
```bash
# Check current schema
sqlite3 pos_erp.db ".schema" > /tmp/current_schema.sql

# Compare with expected schema
diff /tmp/current_schema.sql src/pos_erp/schema.sql
```

### Permission Denied
```bash
# Fix ownership
chown -R deploy:deploy /var/www/pos-erp-v6/pos_erp.db

# Fix permissions
chmod 664 /var/www/pos-erp-v6/pos_erp.db
```

### Corrupt Database
```bash
# Try to recover
sqlite3 pos_erp.db ".recover" > /tmp/recovered.sql
mv pos_erp.db pos_erp.db.corrupt
sqlite3 pos_erp.db < /tmp/recovered.sql
```

---

## Next Steps

After database migration is complete:

1. [03-application-deploy.md](./03-application-deploy.md) — Deploy application
2. [04-ssl-setup.md](./04-ssl-setup.md) — Setup SSL/TLS

---

**Estimated Time:** 15-30 minutes
