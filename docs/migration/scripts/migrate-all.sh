#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — Complete Migration Script
# =============================================================================
# This script automates the migration process to a new VPS.
# 
# Usage:
#   ./migrate-all.sh --old-vps OLD_IP --new-vps NEW_IP --domain DOMAIN
#
# Prerequisites:
#   - SSH access to both old and new VPS
#   - SSH key configured for passwordless access
#   - Root or sudo access on both servers
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
OLD_VPS=""
NEW_VPS=""
DOMAIN="beautynshine.web.id"
SSH_KEY="~/.ssh/id_ed25519"
BACKUP_DIR="/var/www/pos-erp-v6/backups/migration"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/migration-${TIMESTAMP}.log"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --old-vps)
            OLD_VPS="$2"
            shift 2
            ;;
        --new-vps)
            NEW_VPS="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --ssh-key)
            SSH_KEY="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate arguments
if [ -z "$OLD_VPS" ] || [ -z "$NEW_VPS" ]; then
    echo -e "${RED}Error: --old-vps and --new-vps are required${NC}"
    echo "Usage: ./migrate-all.sh --old-vps OLD_IP --new-vps NEW_IP --domain DOMAIN"
    exit 1
fi

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    log "${YELLOW}Migration failed. Check log: $LOG_FILE${NC}"
    exit 1
}

# SSH helper
ssh_cmd() {
    local host=$1
    shift
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no root@"$host" "$@" 2>&1 | tee -a "$LOG_FILE"
}

# =============================================================================
# Pre-Migration Checks
# =============================================================================
log "${BLUE}=== Pre-Migration Checks ===${NC}"

# Check SSH connectivity
log "Checking SSH connectivity..."
ssh_cmd "$OLD_VPS" "echo 'Old VPS connection OK'" || error_exit "Cannot connect to old VPS"
ssh_cmd "$NEW_VPS" "echo 'New VPS connection OK'" || error_exit "Cannot connect to new VPS"

# Check disk space
log "Checking disk space..."
OLD_SPACE=$(ssh_cmd "$OLD_VPS" "df -h / | tail -1 | awk '{print \$5}'" | tail -1)
NEW_SPACE=$(ssh_cmd "$NEW_VPS" "df -h / | tail -1 | awk '{print \$5}'" | tail -1)
log "Old VPS disk usage: $OLD_SPACE"
log "New VPS disk usage: $NEW_SPACE"

# =============================================================================
# Step 1: Backup Database
# =============================================================================
log ""
log "${BLUE}=== Step 1: Backup Database ===${NC}"

ssh_cmd "$OLD_VPS" "
    cd /var/www/pos-erp-v6
    mkdir -p $BACKUP_DIR
    
    # Stop application
    systemctl stop pos-erp
    
    # Backup database
    cp pos_erp.db $BACKUP_DIR/pos_erp_${TIMESTAMP}.db
    
    # Verify integrity
    sqlite3 $BACKUP_DIR/pos_erp_${TIMESTAMP}.db 'PRAGMA integrity_check;'
    
    # Compress
    tar czf $BACKUP_DIR/pos_erp_${TIMESTAMP}.tar.gz -C $BACKUP_DIR pos_erp_${TIMESTAMP}.db
    
    # Backup .env
    cp .env $BACKUP_DIR/env_backup_${TIMESTAMP}
    
    echo 'Backup completed successfully'
" || error_exit "Backup failed"

# =============================================================================
# Step 2: Transfer Files
# =============================================================================
log ""
log "${BLUE}=== Step 2: Transfer Files ===${NC}"

# Transfer database backup
log "Transferring database..."
scp -i "$SSH_KEY" root@"$OLD_VPS":$BACKUP_DIR/pos_erp_${TIMESTAMP}.tar.gz /tmp/ 2>&1 | tee -a "$LOG_FILE"
scp -i "$SSH_KEY" /tmp/pos_erp_${TIMESTAMP}.tar.gz root@"$NEW_VPS":/tmp/ 2>&1 | tee -a "$LOG_FILE"

# Transfer .env
log "Transferring .env..."
scp -i "$SSH_KEY" root@"$OLD_VPS":$BACKUP_DIR/env_backup_${TIMESTAMP} /tmp/env_backup 2>&1 | tee -a "$LOG_FILE"
scp -i "$SSH_KEY" /tmp/env_backup root@"$NEW_VPS":/var/www/pos-erp-v6/.env 2>&1 | tee -a "$LOG_FILE"

# =============================================================================
# Step 3: Setup New Server
# =============================================================================
log ""
log "${BLUE}=== Step 3: Setup New Server ===${NC}"

ssh_cmd "$NEW_VPS" "
    # Create application directory
    mkdir -p /var/www/pos-erp-v6/{logs,backups,static}
    
    # Extract database
    tar xzf /tmp/pos_erp_${TIMESTAMP}.tar.gz -C /tmp/
    mv /tmp/pos_erp_${TIMESTAMP}.db /var/www/pos-erp-v6/pos_erp.db
    
    # Set permissions
    chown -R deploy:deploy /var/www/pos-erp-v6
    chmod 664 /var/www/pos-erp-v6/pos_erp.db
    
    echo 'New server setup completed'
" || error_exit "New server setup failed"

# =============================================================================
# Step 4: Clone Repository
# =============================================================================
log ""
log "${BLUE}=== Step 4: Clone Repository ===${NC}"

ssh_cmd "$NEW_VPS" "
    su - deploy -c '
        cd /var/www/pos-erp-v6
        git clone https://github.com/Polwancuti666/pos-erp-v6.git .
    '
    echo 'Repository cloned'
" || error_exit "Repository clone failed"

# =============================================================================
# Step 5: Setup Python Environment
# =============================================================================
log ""
log "${BLUE}=== Step 5: Setup Python Environment ===${NC}"

ssh_cmd "$NEW_VPS" "
    su - deploy -c '
        cd /var/www/pos-erp-v6
        python3.11 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install gunicorn uvicorn[standard]
    '
    echo 'Python environment setup completed'
" || error_exit "Python setup failed"

# =============================================================================
# Step 6: Build Frontend
# =============================================================================
log ""
log "${BLUE}=== Step 6: Build Frontend ===${NC}"

ssh_cmd "$NEW_VPS" "
    su - deploy -c '
        cd /var/www/pos-erp-v6/frontend
        npm ci
        npm run build
        cp -r dist/* ../static/
    '
    echo 'Frontend built'
" || error_exit "Frontend build failed"

# =============================================================================
# Step 7: Setup Services
# =============================================================================
log ""
log "${BLUE}=== Step 7: Setup Services ===${NC}"

# Copy systemd service file
scp -i "$SSH_KEY" /root/pos-erp-v6/pos-erp.service root@"$NEW_VPS":/etc/systemd/system/pos-erp.service 2>&1 | tee -a "$LOG_FILE"

ssh_cmd "$NEW_VPS" "
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable pos-erp
    
    # Start service
    systemctl start pos-erp
    
    # Wait for startup
    sleep 5
    
    # Check status
    systemctl status pos-erp
    
    echo 'Services setup completed'
" || error_exit "Services setup failed"

# =============================================================================
# Step 8: Verify Migration
# =============================================================================
log ""
log "${BLUE}=== Step 8: Verify Migration ===${NC}"

ssh_cmd "$NEW_VPS" "
    # Test health endpoint
    curl -s http://localhost:8000/health | jq .
    
    # Check database
    sqlite3 /var/www/pos-erp-v6/pos_erp.db 'PRAGMA integrity_check;'
    
    # Check logs
    journalctl -u pos-erp --since '1 minute ago' | tail -5
    
    echo 'Verification completed'
" || error_exit "Verification failed"

# =============================================================================
# Cleanup
# =============================================================================
log ""
log "${BLUE}=== Cleanup ===${NC}"

rm -f /tmp/pos_erp_${TIMESTAMP}.tar.gz /tmp/env_backup

# =============================================================================
# Summary
# =============================================================================
log ""
log "${GREEN}=== Migration Completed Successfully ===${NC}"
log ""
log "Old VPS: $OLD_VPS"
log "New VPS: $NEW_VPS"
log "Domain: $DOMAIN"
log "Timestamp: $TIMESTAMP"
log ""
log "Next steps:"
log "1. Update DNS records to point to $NEW_VPS"
log "2. Setup SSL/TLS: certbot --nginx -d $DOMAIN"
log "3. Configure GitHub Actions secrets"
log "4. Run UAT tests"
log ""
log "Log file: $LOG_FILE"
