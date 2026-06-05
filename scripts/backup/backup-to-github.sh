#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — External Backup to GitHub (Production)
# =============================================================================
# Backup .env + configs + PostgreSQL dump ke GitHub private repo.
# Jalankan di production VPS.
#
# Usage:
#   ./backup-to-github.sh [--quiet]
#
# Cron (daily 3 AM):
#   0 3 * * * /var/www/pos-erp-v6/scripts/backup/backup-to-github.sh --quiet
# =============================================================================

set -e

APP_DIR="/var/www/pos-erp-v6"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="pos-erp-backup-${TIMESTAMP}"
TEMP_DIR="/tmp/github-backup-${TIMESTAMP}"
BACKUP_REPO="pos-erp-backups"
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quiet) QUIET=true; shift ;;
        *) shift ;;
    esac
done

log() {
    if [ "$QUIET" = false ]; then echo "$1"; fi
}

# Load GH token from git credentials
GH_TOKEN=*** ~/.git-credentials | grep github | sed 's/.*:\/\/[^:]*://' | sed 's/@.*//')

log "=== External Backup to GitHub ==="
log "Timestamp: $TIMESTAMP"

# 1. Create temp backup dir
mkdir -p "$TEMP_DIR"

# 2. Backup .env
log "1. Backing up .env..."
cp "$APP_DIR/.env" "$TEMP_DIR/.env"

# 3. Backup PostgreSQL database
log "2. Backing up PostgreSQL database..."
if command -v pg_dump &> /dev/null; then
    # Read DB credentials from .env
    DB_URL=*** "POS_ERP_DATABASE_URL=*** "$APP_DIR/.env" | cut -d'=' -f2-)
    
    if [ -n "$DB_URL" ]; then
        pg_dump "$DB_URL" | gzip > "$TEMP_DIR/pos_erp.sql.gz"
        DB_SIZE=$(du -h "$TEMP_DIR/pos_erp.sql.gz" | cut -f1)
        log "   ✓ Database dumped ($DB_SIZE)"
    else
        log "   ⚠ Database URL not found in .env"
    fi
else
    log "   ⚠ pg_dump not available"
fi

# 4. Backup Nginx config
log "3. Backing up Nginx config..."
if [ -f /etc/nginx/sites-available/pos-erp ]; then
    cp /etc/nginx/sites-available/pos-erp "$TEMP_DIR/nginx-pos-erp.conf"
    log "   ✓ Nginx config backed up"
fi

# 5. Backup Systemd service
log "4. Backing up Systemd service..."
if [ -f /etc/systemd/system/pos-erp.service ]; then
    cp /etc/systemd/system/pos-erp.service "$TEMP_DIR/pos-erp.service"
    log "   ✓ Systemd service backed up"
fi

# 6. Backup Docker files
log "5. Backing up Docker files..."
cp "$APP_DIR/docker-compose.yml" "$TEMP_DIR/" 2>/dev/null && log "   ✓ docker-compose.yml"
cp "$APP_DIR/Dockerfile" "$TEMP_DIR/" 2>/dev/null && log "   ✓ Dockerfile"
cp "$APP_DIR/entrypoint.sh" "$TEMP_DIR/" 2>/dev/null && log "   ✓ entrypoint.sh"

# 7. Create backup info
cat > "$TEMP_DIR/BACKUP_INFO.md" << EOF
# POS ERP Backup

**Created:** $(date '+%Y-%m-%d %H:%M:%S')
**Hostname:** $(hostname)
**Server IP:** $(hostname -I | awk '{print $1}')
**Type:** Full External Backup (Config + Database)

## Contents

| File | Description |
|------|-------------|
| .env | Environment variables |
| pos_erp.sql.gz | PostgreSQL database dump |
| nginx-pos-erp.conf | Nginx configuration |
| pos-erp.service | Systemd service |
| docker-compose.yml | Docker configuration |
| Dockerfile | Docker build |
| entrypoint.sh | Docker entrypoint |

## Restore on New VPS

1. Clone this repo
2. Extract: \`tar xzf *.tar.gz\`
3. Restore database: \`zcat pos_erp.sql.gz | psql -U sa pos_erp\`
4. Copy .env to \`/var/www/pos-erp-v6/.env\`
5. Copy Nginx config to \`/etc/nginx/sites-available/pos-erp\`
6. Copy Systemd service to \`/etc/systemd/system/pos-erp.service\`
7. Start services: \`systemctl start pos-erp nginx\`
EOF

# 8. Clone backup repo and push
log "6. Pushing to GitHub..."
rm -rf "/tmp/clone-${BACKUP_REPO}"
GH_TOKEN=*** gh repo clone Polwancuti666/$BACKUP_REPO "/tmp/clone-${BACKUP_REPO}" 2>/dev/null || {
    cd "/tmp/clone-${BACKUP_REPO}" 2>/dev/null || {
        mkdir -p "/tmp/clone-${BACKUP_REPO}"
        cd "/tmp/clone-${BACKUP_REPO}"
        git init
        git remote add origin "https://github.com/Polwancuti666/$BACKUP_REPO.git"
    }
}

# Copy backup files
cp -r "$TEMP_DIR"/* "/tmp/clone-${BACKUP_REPO}/"

# Update README with backup list
cd "/tmp/clone-${BACKUP_REPO}"
cat > README.md << 'HEADER'
# POS ERP Backups

🔒 **Private Repository** — Automated backups for Beauty & Shine ERP.

## How to Restore

See `BACKUP_INFO.md` in each backup for detailed restore instructions.

Quick restore:
1. Download backup from this repo
2. Copy to new VPS
3. Extract and follow instructions in BACKUP_INFO.md

## Backups

| File | Date | Size |
|------|------|------|
HEADER

# List all backups
for f in pos-erp-backup-*.tar.gz pos-erp-backup-*.sql.gz; do
    if [ -f "$f" ]; then
        SIZE=$(du -h "$f" | cut -f1)
        DATE=$(echo "$f" | grep -oP '\d{8}' | head -1)
        echo "| $f | $DATE | $SIZE |" >> README.md
    fi
done

cat >> README.md << 'FOOTER'

## Security

⚠️ This repo contains sensitive credentials (.env) and database dumps.
Do NOT make this repo public.
FOOTER

# Commit and push
git add -A
git commit -m "backup: $TIMESTAMP" 2>/dev/null || git commit -m "backup: $TIMESTAMP (update)" --allow-empty
git push origin main 2>&1

log ""
log "✓ Backup pushed to GitHub: https://github.com/Polwancuti666/$BACKUP_REPO"

# 9. Cleanup
rm -rf "$TEMP_DIR" "/tmp/clone-${BACKUP_REPO}"

log ""
log "=== External Backup Complete ==="
