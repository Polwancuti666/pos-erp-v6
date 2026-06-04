#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — Backup Cron Setup Script
# =============================================================================
# Sets up automated backup cron jobs.
#
# Usage:
#   ./setup-backup-cron.sh [OPTIONS]
#
# Options:
#   --daily          Enable daily full backup (default: 2 AM)
#   --hourly         Enable hourly quick backup
#   --weekly         Enable weekly full backup (Sunday 3 AM)
#   --remove         Remove all backup cron jobs
#   --show           Show current backup cron jobs
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
APP_DIR="/var/www/pos-erp-v6"
BACKUP_SCRIPTS="$APP_DIR/scripts/backup"
CRON_TAG="# POS-ERP-BACKUP"

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
ENABLE_DAILY=false
ENABLE_HOURLY=false
ENABLE_WEEKLY=false
REMOVE=false
SHOW=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --daily)
            ENABLE_DAILY=true
            shift
            ;;
        --hourly)
            ENABLE_HOURLY=true
            shift
            ;;
        --weekly)
            ENABLE_WEEKLY=true
            shift
            ;;
        --remove)
            REMOVE=true
            shift
            ;;
        --show)
            SHOW=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Show Current Cron Jobs
# =============================================================================
if [ "$SHOW" = true ]; then
    echo -e "${BLUE}=== Current Backup Cron Jobs ===${NC}"
    echo ""
    crontab -l 2>/dev/null | grep "$CRON_TAG" || echo "No backup cron jobs found."
    exit 0
fi

# =============================================================================
# Remove Backup Cron Jobs
# =============================================================================
if [ "$REMOVE" = true ]; then
    echo -e "${YELLOW}Removing backup cron jobs...${NC}"
    
    # Remove lines with our tag
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab -
    
    echo -e "${GREEN}✓ Backup cron jobs removed${NC}"
    exit 0
fi

# =============================================================================
# Check if any option was provided
# =============================================================================
if [ "$ENABLE_DAILY" = false ] && [ "$ENABLE_HOURLY" = false ] && [ "$ENABLE_WEEKLY" = false ]; then
    echo -e "${BLUE}=== Backup Cron Setup ===${NC}"
    echo ""
    echo "Usage: ./setup-backup-cron.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --daily    Enable daily full backup (2 AM)"
    echo "  --hourly   Enable hourly quick backup"
    echo "  --weekly   Enable weekly full backup (Sunday 3 AM)"
    echo "  --remove   Remove all backup cron jobs"
    echo "  --show     Show current backup cron jobs"
    echo ""
    echo "Examples:"
    echo "  ./setup-backup-cron.sh --daily"
    echo "  ./setup-backup-cron.sh --daily --weekly"
    echo "  ./setup-backup-cron.sh --show"
    exit 0
fi

# =============================================================================
# Setup Cron Jobs
# =============================================================================
echo -e "${BLUE}=== Setting up Backup Cron Jobs ===${NC}"
echo ""

# Make scripts executable
chmod +x "$BACKUP_SCRIPTS"/*.sh

# Get current crontab
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

# Remove existing backup cron jobs
CURRENT_CRON=$(echo "$CURRENT_CRON" | grep -v "$CRON_TAG")

# Add daily full backup
if [ "$ENABLE_DAILY" = true ]; then
    echo -e "${GREEN}✓ Enabling daily full backup (2 AM)${NC}"
    CURRENT_CRON="$CURRENT_CRON
0 2 * * * $BACKUP_SCRIPTS/backup-full.sh --quiet $CRON_TAG"
fi

# Add hourly quick backup
if [ "$ENABLE_HOURLY" = true ]; then
    echo -e "${GREEN}✓ Enabling hourly quick backup${NC}"
    CURRENT_CRON="$CURRENT_CRON
0 * * * * $BACKUP_SCRIPTS/backup-quick.sh --quiet $CRON_TAG"
fi

# Add weekly full backup
if [ "$ENABLE_WEEKLY" = true ]; then
    echo -e "${GREEN}✓ Enabling weekly full backup (Sunday 3 AM)${NC}"
    CURRENT_CRON="$CURRENT_CRON
0 3 * * 0 $BACKUP_SCRIPTS/backup-full.sh --quiet $CRON_TAG"
fi

# Install new crontab
echo "$CURRENT_CRON" | grep -v '^$' | crontab -

echo ""
echo -e "${GREEN}=== Cron Jobs Installed ===${NC}"
echo ""
echo "Current backup cron jobs:"
crontab -l 2>/dev/null | grep "$CRON_TAG"

echo ""
echo "To view logs:"
echo "  tail -f /var/www/pos-erp-v6/backups/backup.log"
echo ""
echo "To test backup:"
echo "  $BACKUP_SCRIPTS/backup-full.sh"
echo ""
echo "To remove all backup cron jobs:"
echo "  ./setup-backup-cron.sh --remove"
