#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — Complete Backup (Local + External)
# =============================================================================
# Backup ke local DAN external sekaligus.
#
# Usage:
#   ./backup-complete.sh [OPTIONS]
#
# Options:
#   --external       Juga backup ke external (GitHub/Telegram/Email)
#   --quiet          Suppress output
#
# Cron example (daily at 2 AM):
#   0 2 * * * /var/www/pos-erp-v6/scripts/backup/backup-complete.sh --external --quiet
# =============================================================================

set -e

APP_DIR="/var/www/pos-erp-v6"
SCRIPTS_DIR="$APP_DIR/scripts/backup"
QUIET=false
EXTERNAL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --external)
            EXTERNAL=true
            shift
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

# Helper
log() {
    if [ "$QUIET" = false ]; then
        echo "$1"
    fi
}

# =============================================================================
# Run Backups
# =============================================================================
log "=== Complete Backup ==="
log ""

# 1. Local backup
log "1. Running local backup..."
$SCRIPTS_DIR/backup-full.sh --quiet

# 2. External backup (optional)
if [ "$EXTERNAL" = true ]; then
    log ""
    log "2. Running external backup..."
    
    # Try GitHub first, then Telegram, then email
    $SCRIPTS_DIR/backup-external.sh --dest github --quiet 2>/dev/null || {
        log "   GitHub backup failed, trying Telegram..."
        $SCRIPTS_DIR/backup-external.sh --dest telegram --quiet 2>/dev/null || {
            log "   Telegram backup failed, trying email..."
            $SCRIPTS_DIR/backup-external.sh --dest email --quiet 2>/dev/null || {
                log "   All external backups failed"
            }
        }
    }
fi

log ""
log "=== Complete Backup Done ==="
