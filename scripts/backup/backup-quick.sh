#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — Quick Backup Script
# =============================================================================
# Quick backup for daily use. Creates a lightweight backup of essential files.
#
# Usage:
#   ./backup-quick.sh [OPTIONS]
#
# Options:
#   --output DIR     Backup output directory (default: /var/www/pos-erp-v6/backups)
#   --quiet          Suppress output
#
# Cron example (daily at 2 AM):
#   0 2 * * * /var/www/pos-erp-v6/scripts/backup/backup-quick.sh --quiet
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
APP_DIR="/var/www/pos-erp-v6"
DB_PATH="$APP_DIR/pos_erp.db"
ENV_PATH="$APP_DIR/.env"
BACKUP_DIR="$APP_DIR/backups"
QUIET=false
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="quick-backup-${TIMESTAMP}"

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================
log() {
    if [ "$QUIET" = false ]; then
        echo "$1"
    fi
}

# =============================================================================
# Backup
# =============================================================================
log "=== Quick Backup ==="
log "Timestamp: $TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Stop application briefly
systemctl stop pos-erp 2>/dev/null || true
sleep 1

# Backup database
log "Backing up database..."
cp "$DB_PATH" "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db"

# Verify integrity
INTEGRITY=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db" "PRAGMA integrity_check;")
if [ "$INTEGRITY" != "ok" ]; then
    log "ERROR: Database integrity check failed"
    exit 1
fi

# Restart application
systemctl start pos-erp 2>/dev/null || true

# Backup .env
log "Backing up .env..."
cp "$ENV_PATH" "$BACKUP_DIR/$BACKUP_NAME/.env"

# Compress
log "Compressing..."
cd "$BACKUP_DIR"
tar czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# Cleanup old quick backups (keep last 7 days)
find "$BACKUP_DIR" -name "quick-backup-*.tar.gz" -mtime +7 -delete 2>/dev/null || true

# Summary
BACKUP_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)
log ""
log "✓ Backup complete: ${BACKUP_NAME}.tar.gz ($BACKUP_SIZE)"
log "  Location: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"

# Output path for automation
if [ "$QUIET" = true ]; then
    echo "$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
fi
