#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — External Backup Setup Guide
# =============================================================================
# Panduan lengkap untuk setup backup ke external storage.
#
# Problem:
#   Jika VPS lama mati, backup di local VPS juga hilang.
#
# Solution:
#   Backup ke external storage yang bisa diakses dari mana saja.
#
# Options:
#   1. GitHub Private Repo (recommended)
#   2. Telegram
#   3. Email
#   4. Cloud Storage (S3, R2, etc.)
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/var/www/pos-erp-v6"
SCRIPTS_DIR="$APP_DIR/scripts/backup"

# =============================================================================
# Display Menu
# =============================================================================
show_menu() {
    echo -e "${BLUE}=== External Backup Setup ===${NC}"
    echo ""
    echo "Pilih destinasi backup:"
    echo ""
    echo "  1) GitHub Private Repo (recommended)"
    echo "  2) Telegram"
    echo "  3) Email"
    echo "  4) Semua (GitHub + Telegram + Email)"
    echo "  5) Test backup sekarang"
    echo "  6) Setup cron otomatis"
    echo "  7) Keluar"
    echo ""
    read -p "Pilih [1-7]: " choice
}

# =============================================================================
# Setup GitHub Backup
# =============================================================================
setup_github() {
    echo ""
    echo -e "${BLUE}=== Setup GitHub Backup ===${NC}"
    echo ""
    
    # Check gh CLI
    if ! command -v gh &> /dev/null; then
        echo -e "${YELLOW}GitHub CLI belum terinstall.${NC}"
        echo ""
        echo "Install GitHub CLI:"
        echo "  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
        echo "  echo 'deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
        echo "  sudo apt update && sudo apt install gh"
        echo ""
        echo "Setelah install, jalankan: gh auth login"
        return 1
    fi
    
    # Check auth
    if ! gh auth status &> /dev/null; then
        echo -e "${YELLOW}GitHub CLI belum terautentikasi.${NC}"
        echo ""
        echo "Jalankan: gh auth login"
        return 1
    fi
    
    echo -e "${GREEN}✓ GitHub CLI sudah terinstall dan terautentikasi${NC}"
    echo ""
    
    # Create backup repo
    read -p "Buat private repo 'pos-erp-backups'? [y/N]: " create_repo
    if [[ "$create_repo" =~ ^[Yy]$ ]]; then
        gh repo create Polwancuti666/pos-erp-backups --private --description "POS ERP Automated Backups"
        echo -e "${GREEN}✓ Repository created: https://github.com/Polwancuti666/pos-erp-backups${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}✓ GitHub backup siap!${NC}"
    echo ""
    echo "Untuk backup ke GitHub:"
    echo "  $SCRIPTS_DIR/backup-external.sh --dest github"
}

# =============================================================================
# Setup Telegram Backup
# =============================================================================
setup_telegram() {
    echo ""
    echo -e "${BLUE}=== Setup Telegram Backup ===${NC}"
    echo ""
    
    echo "Untuk backup ke Telegram, kamu perlu:"
    echo "  1. Telegram Bot Token"
    echo "  2. Chat ID"
    echo ""
    
    # Get bot token
    read -p "Masukkan Telegram Bot Token: " bot_token
    
    if [ -z "$bot_token" ]; then
        echo -e "${RED}Bot token tidak boleh kosong${NC}"
        return 1
    fi
    
    # Get chat ID
    read -p "Masukkan Telegram Chat ID: " chat_id
    
    if [ -z "$chat_id" ]; then
        echo -e "${RED}Chat ID tidak boleh kosong${NC}"
        return 1
    fi
    
    # Save to .env
    echo "" >> "$APP_DIR/.env"
    echo "# Telegram Backup Config" >> "$APP_DIR/.env"
    echo "TELEGRAM_BOT_TOKEN=$bot_token" >> "$APP_DIR/.env"
    echo "TELEGRAM_CHAT_ID=$chat_id" >> "$APP_DIR/.env"
    
    echo ""
    echo -e "${GREEN}✓ Telegram backup siap!${NC}"
    echo ""
    echo "Untuk backup ke Telegram:"
    echo "  $SCRIPTS_DIR/backup-external.sh --dest telegram"
}

# =============================================================================
# Setup Email Backup
# =============================================================================
setup_email() {
    echo ""
    echo -e "${BLUE}=== Setup Email Backup ===${NC}"
    echo ""
    
    # Check mailutils
    if ! command -v mail &> /dev/null; then
        echo -e "${YELLOW}mailutils belum terinstall.${NC}"
        echo ""
        echo "Install: apt install mailutils"
        read -p "Install sekarang? [y/N]: " install_mail
        if [[ "$install_mail" =~ ^[Yy]$ ]]; then
            apt install -y mailutils
        else
            return 1
        fi
    fi
    
    # Get email
    read -p "Masukkan email tujuan backup: " email_to
    
    if [ -z "$email_to" ]; then
        echo -e "${RED}Email tidak boleh kosong${NC}"
        return 1
    fi
    
    # Save to .env
    echo "" >> "$APP_DIR/.env"
    echo "# Email Backup Config" >> "$APP_DIR/.env"
    echo "BACKUP_EMAIL=$email_to" >> "$APP_DIR/.env"
    
    echo ""
    echo -e "${GREEN}✓ Email backup siap!${NC}"
    echo ""
    echo "Untuk backup ke email:"
    echo "  $SCRIPTS_DIR/backup-external.sh --dest email"
}

# =============================================================================
# Setup All
# =============================================================================
setup_all() {
    echo ""
    echo -e "${BLUE}=== Setup Semua Destinasi ===${NC}"
    echo ""
    
    setup_github || true
    setup_telegram || true
    setup_email || true
    
    echo ""
    echo -e "${GREEN}✓ Semua destinasi backup sudah di-setup!${NC}"
    echo ""
    echo "Untuk backup ke semua destinasi:"
    echo "  $SCRIPTS_DIR/backup-external.sh --dest all"
}

# =============================================================================
# Test Backup
# =============================================================================
test_backup() {
    echo ""
    echo -e "${BLUE}=== Test Backup ===${NC}"
    echo ""
    
    read -p "Pilih destinasi test (github/telegram/email/all): " dest
    
    case "$dest" in
        github|telegram|email|all)
            $SCRIPTS_DIR/backup-external.sh --dest "$dest"
            ;;
        *)
            echo -e "${RED}Destinasi tidak valid${NC}"
            ;;
    esac
}

# =============================================================================
# Setup Cron
# =============================================================================
setup_cron() {
    echo ""
    echo -e "${BLUE}=== Setup Cron Otomatis ===${NC}"
    echo ""
    
    read -p "Backup ke GitHub setiap hari jam 3 AM? [y/N]: " daily_github
    if [[ "$daily_github" =~ ^[Yy]$ ]]; then
        (crontab -l 2>/dev/null; echo "0 3 * * * $SCRIPTS_DIR/backup-external.sh --dest github --quiet # POS-ERP-EXTERNAL-BACKUP") | crontab -
        echo -e "${GREEN}✓ Cron GitHub backup ditambahkan${NC}"
    fi
    
    read -p "Backup ke Telegram setiap hari jam 4 AM? [y/N]: " daily_telegram
    if [[ "$daily_telegram" =~ ^[Yy]$ ]]; then
        (crontab -l 2>/dev/null; echo "0 4 * * * $SCRIPTS_DIR/backup-external.sh --dest telegram --quiet # POS-ERP-EXTERNAL-BACKUP") | crontab -
        echo -e "${GREEN}✓ Cron Telegram backup ditambahkan${NC}"
    fi
    
    read -p "Backup ke email setiap hari jam 5 AM? [y/N]: " daily_email
    if [[ "$daily_email" =~ ^[Yy]$ ]]; then
        (crontab -l 2>/dev/null; echo "0 5 * * * $SCRIPTS_DIR/backup-external.sh --dest email --quiet # POS-ERP-EXTERNAL-BACKUP") | crontab -
        echo -e "${GREEN}✓ Cron Email backup ditambahkan${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}✓ Cron setup complete!${NC}"
    echo ""
    echo "Current cron jobs:"
    crontab -l 2>/dev/null | grep "POS-ERP-EXTERNAL-BACKUP" || echo "No external backup cron jobs"
}

# =============================================================================
# Main Loop
# =============================================================================
while true; do
    show_menu
    
    case $choice in
        1) setup_github ;;
        2) setup_telegram ;;
        3) setup_email ;;
        4) setup_all ;;
        5) test_backup ;;
        6) setup_cron ;;
        7) exit 0 ;;
        *) echo -e "${RED}Pilihan tidak valid${NC}" ;;
    esac
    
    echo ""
    read -p "Tekan Enter untuk kembali ke menu..."
done
