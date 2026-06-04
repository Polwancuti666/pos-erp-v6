#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — External Backup Script
# =============================================================================
# Backup ke external storage sehingga bisa restore dari mana saja
# meskipun VPS lama mati.
#
# Supported destinations:
#   1. GitHub Private Repository (recommended untuk .env + configs)
#   2. Telegram (send backup ke chat)
#   3. Email (send backup ke email)
#   4. Cloudflare R2 / S3 (optional)
#
# Usage:
#   ./backup-external.sh --dest DESTINATION [OPTIONS]
#
# Options:
#   --dest github      Backup ke GitHub private repo
#   --dest telegram    Backup ke Telegram chat
#   --dest email       Backup ke email
#   --dest all         Backup ke semua destinasi
#   --quiet            Suppress output
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
APP_DIR="/var/www/pos-erp-v6"
DB_PATH="$APP_DIR/pos_erp.db"
ENV_PATH="$APP_DIR/.env"
BACKUP_DIR="$APP_DIR/backups/external"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="pos-erp-external-${TIMESTAMP}"
DEST=""
QUIET=false

# GitHub config
GITHUB_BACKUP_REPO="pos-erp-backups"
GITHUB_ORG="Polwancuti666"

# Telegram config (will be read from .env)
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""

# Email config
EMAIL_TO=""

# =============================================================================
# Colors
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --dest)
            DEST="$2"
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
        echo -e "$1"
    fi
}

error_exit() {
    echo -e "${RED}ERROR: $1${NC}"
    exit 1
}

# =============================================================================
# Load Configuration
# =============================================================================
load_config() {
    # Load Telegram config from .env
    if [ -f "$APP_DIR/.env" ]; then
        TELEGRAM_BOT_TOKEN=*** "TELEGRAM_BOT_TOKEN=*** "$APP_DIR/.env" | cut -d'=' -f2)
        TELEGRAM_CHAT_ID=*** "TELEGRAM_CHAT_ID=*** "$APP_DIR/.env" | cut -d'=' -f2)
    fi
}

# =============================================================================
# Create Backup Package
# =============================================================================
create_backup_package() {
    log "${BLUE}=== Creating External Backup Package ===${NC}"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    
    # Stop application briefly for consistent backup
    systemctl stop pos-erp 2>/dev/null || true
    sleep 2
    
    # 1. Backup database
    log "1. Backing up database..."
    cp "$DB_PATH" "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db"
    
    # Verify integrity
    INTEGRITY=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db" "PRAGMA integrity_check;")
    if [ "$INTEGRITY" != "ok" ]; then
        error_exit "Database integrity check failed"
    fi
    log "   ✓ Database backed up"
    
    # Restart application
    systemctl start pos-erp 2>/dev/null || true
    
    # 2. Backup .env
    log "2. Backing up .env..."
    cp "$ENV_PATH" "$BACKUP_DIR/$BACKUP_NAME/.env"
    log "   ✓ .env backed up"
    
    # 3. Backup Nginx config
    log "3. Backing up Nginx config..."
    if [ -f "/etc/nginx/sites-available/pos-erp" ]; then
        cp "/etc/nginx/sites-available/pos-erp" "$BACKUP_DIR/$BACKUP_NAME/nginx-pos-erp.conf"
        log "   ✓ Nginx config backed up"
    fi
    
    # 4. Backup Systemd service
    log "4. Backing up Systemd service..."
    if [ -f "/etc/systemd/system/pos-erp.service" ]; then
        cp "/etc/systemd/system/pos-erp.service" "$BACKUP_DIR/$BACKUP_NAME/pos-erp.service"
        log "   ✓ Systemd service backed up"
    fi
    
    # 5. Create backup info
    log "5. Creating backup info..."
    cat > "$BACKUP_DIR/$BACKUP_NAME/BACKUP_INFO.md" << EOF
# Backup Information

**Created:** $(date '+%Y-%m-%d %H:%M:%S')
**Hostname:** $(hostname)
**Server IP:** $(hostname -I | awk '{print $1}')
**Backup Type:** External Backup

## Contents

- pos_erp.db — SQLite database
- .env — Environment variables
- nginx-pos-erp.conf — Nginx configuration
- pos-erp.service — Systemd service file

## Database Statistics

$(sqlite3 "$DB_PATH" "SELECT 'Branches: ' || COUNT(*) FROM branch;")
$(sqlite3 "$DB_PATH" "SELECT 'Users: ' || COUNT(*) FROM users;")
$(sqlite3 "$DB_PATH" "SELECT 'Products: ' || COUNT(*) FROM product;")
$(sqlite3 "$DB_PATH" "SELECT 'Transactions: ' || COUNT(*) FROM txn;")

## Restore Instructions

1. Copy this backup to new VPS
2. Extract: tar xzf backup.tar.gz
3. Run: ./scripts/backup/restore-full.sh --backup /path/to/backup
4. Or follow: docs/migration/02-database-migration.md
EOF
    
    # 6. Compress
    log "6. Compressing backup..."
    cd "$BACKUP_DIR"
    tar czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    rm -rf "$BACKUP_NAME"
    
    BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    log ""
    log "✓ Backup package created: ${BACKUP_NAME}.tar.gz ($BACKUP_SIZE)"
    log "  Location: $BACKUP_FILE"
    
    echo "$BACKUP_FILE"
}

# =============================================================================
# Backup to GitHub
# =============================================================================
backup_to_github() {
    log ""
    log "${BLUE}=== Backup to GitHub ===${NC}"
    
    BACKUP_FILE="$1"
    
    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        log "${YELLOW}GitHub CLI not installed. Skipping GitHub backup.${NC}"
        log "Install: https://cli.github.com/"
        return 1
    fi
    
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        log "${YELLOW}GitHub CLI not authenticated. Skipping GitHub backup.${NC}"
        log "Run: gh auth login"
        return 1
    fi
    
    # Create backup repo if not exists
    if ! gh repo view "$GITHUB_ORG/$GITHUB_BACKUP_REPO" &> /dev/null; then
        log "Creating private backup repository..."
        gh repo create "$GITHUB_ORG/$GITHUB_BACKUP_REPO" --private --description "POS ERP Automated Backups"
    fi
    
    # Clone backup repo
    TEMP_DIR="/tmp/github-backup-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$TEMP_DIR"
    
    gh repo clone "$GITHUB_ORG/$GITHUB_BACKUP_REPO" "$TEMP_DIR" 2>/dev/null || {
        cd "$TEMP_DIR"
        git init
        git remote add origin "https://github.com/$GITHUB_ORG/$GITHUB_BACKUP_REPO.git"
    }
    
    # Copy backup to repo
    cp "$BACKUP_FILE" "$TEMP_DIR/"
    
    # Create README
    cat > "$TEMP_DIR/README.md" << EOF
# POS ERP Backups

Automated backups for Beauty & Shine ERP.

**Last backup:** $(date '+%Y-%m-%d %H:%M:%S')
**Server:** $(hostname) ($(hostname -I | awk '{print $1}'))

## Backups

$(ls -lh "$TEMP_DIR"/*.tar.gz 2>/dev/null | awk '{print "- " $9 " (" $5 ")"}')

## Restore

1. Download backup file
2. Copy to new VPS
3. Run: \`./scripts/backup/restore-full.sh --backup backup.tar.gz\`
EOF
    
    # Commit and push
    cd "$TEMP_DIR"
    git add -A
    git commit -m "backup: $(date '+%Y-%m-%d %H:%M:%S')" || true
    git push origin main 2>/dev/null || git push -u origin main 2>/dev/null
    
    log "✓ Backup uploaded to GitHub: https://github.com/$GITHUB_ORG/$GITHUB_BACKUP_REPO"
    
    # Cleanup
    rm -rf "$TEMP_DIR"
}

# =============================================================================
# Backup to Telegram
# =============================================================================
backup_to_telegram() {
    log ""
    log "${BLUE}=== Backup to Telegram ===${NC}"
    
    BACKUP_FILE="$1"
    BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
    
    # Check if Telegram config exists
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
        log "${YELLOW}Telegram config not found. Skipping Telegram backup.${NC}"
        log "Add to .env:"
        log "  TELEGRAM_BOT_TOKEN=your_bot_token"
        log "  TELEGRAM_CHAT_ID=your_chat_id"
        return 1
    fi
    
    # Telegram max file size: 50MB
    MAX_SIZE=$((50 * 1024 * 1024))
    
    if [ "$BACKUP_SIZE" -gt "$MAX_SIZE" ]; then
        log "${YELLOW}Backup too large for Telegram ($(($BACKUP_SIZE / 1024 / 1024))MB > 50MB). Skipping.${NC}"
        return 1
    fi
    
    # Send file
    log "Sending backup to Telegram..."
    
    RESPONSE=$(curl -s -F "chat_id=$TELEGRAM_CHAT_ID" \
        -F "document=@$BACKUP_FILE" \
        -F "caption=📦 POS ERP Backup $(date '+%Y-%m-%d %H:%M:%S')" \
        "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument")
    
    if echo "$RESPONSE" | grep -q '"ok":true'; then
        log "✓ Backup sent to Telegram"
    else
        log "${YELLOW}Failed to send to Telegram${NC}"
        log "Response: $RESPONSE"
    fi
}

# =============================================================================
# Backup to Email
# =============================================================================
backup_to_email() {
    log ""
    log "${BLUE}=== Backup to Email ===${NC}"
    
    BACKUP_FILE="$1"
    BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
    
    # Check if email config exists
    if [ -z "$EMAIL_TO" ]; then
        log "${YELLOW}Email config not found. Skipping email backup.${NC}"
        log "Add to .env:"
        log "  BACKUP_EMAIL=your@email.com"
        return 1
    fi
    
    # Email max attachment: ~25MB
    MAX_SIZE=$((25 * 1024 * 1024))
    
    if [ "$BACKUP_SIZE" -gt "$MAX_SIZE" ]; then
        log "${YELLOW}Backup too large for email ($(($BACKUP_SIZE / 1024 / 1024))MB > 25MB). Skipping.${NC}"
        return 1
    fi
    
    # Send email
    log "Sending backup to email..."
    
    if command -v mail &> /dev/null; then
        echo "POS ERP Backup $(date '+%Y-%m-%d %H:%M:%S')" | \
            mail -s "POS ERP Backup" -A "$BACKUP_FILE" "$EMAIL_TO"
        log "✓ Backup sent to email: $EMAIL_TO"
    else
        log "${YELLOW}mail command not found. Skipping email backup.${NC}"
        log "Install: apt install mailutils"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    log "${BLUE}=== Beauty & Shine ERP — External Backup ===${NC}"
    log ""
    
    # Load config
    load_config
    
    # Validate destination
    if [ -z "$DEST" ]; then
        echo -e "${RED}Error: Destination is required${NC}"
        echo ""
        echo "Usage: ./backup-external.sh --dest DESTINATION"
        echo ""
        echo "Destinations:"
        echo "  github    — Backup ke GitHub private repo"
        echo "  telegram  — Backup ke Telegram chat"
        echo "  email     — Backup ke email"
        echo "  all       — Backup ke semua destinasi"
        exit 1
    fi
    
    # Create backup package
    BACKUP_FILE=$(create_backup_package)
    
    # Send to destinations
    case "$DEST" in
        github)
            backup_to_github "$BACKUP_FILE"
            ;;
        telegram)
            backup_to_telegram "$BACKUP_FILE"
            ;;
        email)
            backup_to_email "$BACKUP_FILE"
            ;;
        all)
            backup_to_github "$BACKUP_FILE" || true
            backup_to_telegram "$BACKUP_FILE" || true
            backup_to_email "$BACKUP_FILE" || true
            ;;
        *)
            error_exit "Unknown destination: $DEST"
            ;;
    esac
    
    # Summary
    log ""
    log "${GREEN}=== External Backup Complete ===${NC}"
    log ""
    log "Backup file: $BACKUP_FILE"
    log "Destination: $DEST"
    log ""
    log "To restore on new VPS:"
    log "  1. Download backup from $DEST"
    log "  2. Copy to new VPS"
    log "  3. Run: ./scripts/backup/restore-full.sh --backup backup.tar.gz"
}

# Run main
main
