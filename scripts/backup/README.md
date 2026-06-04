# Backup & Restore System

Complete backup and restore system for Beauty & Shine ERP.

## Overview

This system provides:

- **Automated daily backups** — Database, .env, configs
- **Quick hourly backups** — Lightweight database-only backups
- **Full restore capability** — Restore on any new VPS
- **Backup verification** — Verify backups before restore
- **Cron job management** — Easy setup and removal
- **External backup** — Backup ke GitHub/Telegram/Email (anti hilang!)
---

## Quick Start
## Quick Start

### Create a Backup Now

```bash
# Full backup (database + .env + configs)
./scripts/backup/backup-full.sh

# Quick backup (database + .env only)
./scripts/backup/backup-quick.sh

# External backup (GitHub/Telegram/Email)
#./scripts/backup/backup-external.sh --dest github
#./scripts/backup/backup-external.sh --dest telegram
#./scripts/backup/backup-external.sh --dest all

# Complete backup (local + external)
#./scripts/backup/backup-complete.sh --external
```

### Setup Automated Backups

```bash
# Daily backup at 2 AM
./scripts/backup/setup-backup-cron.sh --daily

# Daily + Weekly backup
./scripts/backup/setup-backup-cron.sh --daily --weekly

# Hourly quick backup
./scripts/backup/setup-backup-cron.sh --hourly
```

### Restore on New VPS

```bash
# Restore from backup
./scripts/backup/restore-full.sh --backup /path/to/backup.tar.gz

# Dry run (see what would be done)
./scripts/backup/restore-full.sh --backup /path/to/backup.tar.gz --dry-run
```

### Verify Backup

```bash
# Verify backup is complete and ready
./scripts/backup/verify-backup.sh --backup /path/to/backup.tar.gz
```

### Setup External Backup

```bash
# Interactive setup
#./scripts/backup/setup-external-backup.sh

# Or manual:
# Backup ke GitHub
#./scripts/backup/backup-external.sh --dest github

# Backup ke Telegram
#./scripts/backup/backup-external.sh --dest telegram

# Backup ke semua destinasi
#./scripts/backup/backup-external.sh --dest all
```
---

## Scripts

### backup-full.sh

Full backup of the entire system.

**What's backed up:**
- SQLite database
- Environment file (.env)
- Nginx configuration
- Systemd service file
- SSL certificates (if exists)
- Git repository bundle
- Application scripts

**Usage:**
```bash
./scripts/backup/backup-full.sh [OPTIONS]

Options:
  --output DIR     Backup output directory (default: /var/www/pos-erp-v6/backups)
  --keep DAYS      Days to keep old backups (default: 30)
  --no-compress    Don't compress backup
  --quiet          Suppress output
```

**Example:**
```bash
# Standard backup
./scripts/backup/backup-full.sh

# Backup to custom location
./scripts/backup/backup-full.sh --output /mnt/external/backups

# Keep backups for 60 days
./scripts/backup/backup-full.sh --keep 60
```

---

### backup-quick.sh

Quick backup for daily use.

**What's backed up:**
- SQLite database
- Environment file (.env)

**Usage:**
```bash
./scripts/backup/backup-quick.sh [OPTIONS]

Options:
  --output DIR     Backup output directory (default: /var/www/pos-erp-v6/backups)
  --quiet          Suppress output
```

**Example:**
```bash
# Standard quick backup
./scripts/backup/backup-quick.sh
```

---

### restore-full.sh

Full restore on a new VPS.

**What's restored:**
- SQLite database
- Environment file (.env)
- Nginx configuration
- Systemd service file
- SSL certificates
- Git repository
- Python environment
- Frontend build

**Usage:**
```bash
./scripts/backup/restore-full.sh --backup BACKUP_PATH [OPTIONS]

Options:
  --backup PATH    Path to backup file (.tar.gz) or directory
  --domain DOMAIN  Domain name (default: beautynshine.web.id)
  --skip-ssl       Skip SSL certificate restore
  --skip-nginx     Skip Nginx configuration restore
  --skip-systemd   Skip Systemd service restore
  --dry-run        Show what would be done without making changes
  --yes            Skip confirmation prompts
```

**Example:**
```bash
# Standard restore
./scripts/backup/restore-full.sh --backup /tmp/pos-erp-backup-20260604_020000.tar.gz

# Restore with different domain
./scripts/backup/restore-full.sh --backup /tmp/backup.tar.gz --domain example.com

# Dry run
./scripts/backup/restore-full.sh --backup /tmp/backup.tar.gz --dry-run
```

---

### verify-backup.sh

Verify backup is complete and ready for restore.

**What's checked:**
- Required files exist
- Database integrity
- Environment file contents
- File sizes
- Backup age

**Usage:**
```bash
./scripts/backup/verify-backup.sh --backup BACKUP_PATH [OPTIONS]

Options:
  --backup PATH    Path to backup file (.tar.gz) or directory
  --verbose        Show detailed output
```

**Example:**
```bash
# Verify backup
./scripts/backup/verify-backup.sh --backup /tmp/backup.tar.gz

# Verbose output
./scripts/backup/verify-backup.sh --backup /tmp/backup.tar.gz --verbose
```

---

### setup-backup-cron.sh

Setup automated backup cron jobs.

**Usage:**
```bash
./scripts/backup/setup-backup-cron.sh [OPTIONS]

Options:
  --daily    Enable daily full backup (2 AM)
  --hourly   Enable hourly quick backup
  --weekly   Enable weekly full backup (Sunday 3 AM)
  --remove   Remove all backup cron jobs
  --show     Show current backup cron jobs
```

**Example:**
```bash
# Daily backup
./scripts/backup/setup-backup-cron.sh --daily

# Daily + Weekly backup
./scripts/backup/setup-backup-cron.sh --daily --weekly

# Show current cron jobs
./scripts/backup/setup-backup-cron.sh --show

# Remove all backup cron jobs
./scripts/backup/setup-backup-cron.sh --remove
```

---

## Backup Location

Default backup location:
```
/var/www/pos-erp-v6/backups/
├── pos-erp-backup-20260604_020000.tar.gz
├── pos-erp-backup-20260603_020000.tar.gz
├── quick-backup-20260604_140000.tar.gz
├── quick-backup-20260604_130000.tar.gz
└── backup.log
```

## External Backup Destinations

Backup ke external storage agar bisa restore dari mana saja meskipun VPS lama mati.

### 1. GitHub Private Repo (Recommended)

**Kelebihan:**
- Gratis untuk private repo
- Version control (bisa lihat history backup)
- Bisa diakses dari mana saja
- Tidak hilang kalau VPS mati

**Setup:**
```bash
# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh

# Login
gh auth login

# Create backup repo
gh repo create Polwancuti666/pos-erp-backups --private

# Backup
#./scripts/backup/backup-external.sh --dest github
```

**Restore:**
```bash
# Clone backup repo
gh repo clone Polwancuti666/pos-erp-backups
cd pos-erp-backups

# Find latest backup
ls -lh *.tar.gz

# Restore
#./scripts/backup/restore-full.sh --backup pos-erp-backup-*.tar.gz
```

### 2. Telegram

**Kelebihan:**
- Mudah diakses dari HP
- Notifikasi langsung ke HP
- Gratis

**Kekurangan:**
- Max file size 50MB
- Tidak ada version control

**Setup:**
```bash
# 1. Buat Telegram Bot via @BotFather
# 2. Dapatkan bot token
# 3. Dapatkan chat ID (kirim pesan ke bot, lalu cek https://api.telegram.org/bot<TOKEN>/getUpdates)
# 4. Tambahkan ke .env:
#    TELEGRAM_BOT_TOKEN=your_b...
#    TELEGRAM_CHAT_ID=your_chat_id

# Backup
#./scripts/backup/backup-external.sh --dest telegram
```

### 3. Email

**Kelebihan:**
- Mudah diakses
- Bisa auto-forward ke email lain

**Kekurangan:**
- Max attachment ~25MB
- Butuh mailutils installed

**Setup:**
```bash
# Install mailutils
apt install mailutils

# Tambahkan ke .env:
#    BACKUP_EMAIL=your@email.com

# Backup
#./scripts/backup/backup-external.sh --dest email
```

### 4. Semua Destinasi

```bash
# Backup ke semua destinasi sekaligus
#./scripts/backup/backup-external.sh --dest all
```
---

## Restore Process

### On New VPS

1. **Copy backup to new VPS**
   ```bash
   scp /var/www/pos-erp-v6/backups/pos-erp-backup-*.tar.gz root@NEW_VPS:/tmp/
   ```

2. **Run restore script**
   ```bash
   ssh root@NEW_VPS
   cd /var/www/pos-erp-v6
   ./scripts/backup/restore-full.sh --backup /tmp/pos-erp-backup-*.tar.gz
   ```

3. **Verify restore**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Update DNS**
   Point your domain to the new VPS IP.

5. **Setup SSL**
   ```bash
   certbot --nginx -d beautynshine.web.id
   ```

---

## Cron Schedule

| Schedule | Script | Description |
|----------|--------|-------------|
| Daily 2 AM | backup-full.sh | Full backup |
| Hourly | backup-quick.sh | Quick backup |
| Sunday 3 AM | backup-full.sh | Weekly full backup |

---

## Monitoring

### View Backup Logs

```bash
# Real-time logs
tail -f /var/www/pos-erp-v6/backups/backup.log

# Recent backups
ls -lh /var/www/pos-erp-v6/backups/*.tar.gz | tail -10
```

### Check Backup Status

```bash
# List backups
ls -lh /var/www/pos-erp-v6/backups/

# Check latest backup
ls -lt /var/www/pos-erp-v6/backups/*.tar.gz | head -1

# Verify latest backup
./scripts/backup/verify-backup.sh --backup $(ls -t /var/www/pos-erp-v6/backups/*.tar.gz | head -1)
```

---

## Troubleshooting

### Backup Fails

**Problem:** Backup script fails with permission error

**Solution:**
```bash
# Fix permissions
chown -R deploy:deploy /var/www/pos-erp-v6
chmod +x /var/www/pos-erp-v6/scripts/backup/*.sh
```

---

**Problem:** Database integrity check fails

**Solution:**
```bash
# Check database
sqlite3 /var/www/pos-erp-v6/pos_erp.db "PRAGMA integrity_check;"

# If corrupt, restore from last good backup
./scripts/backup/restore-full.sh --backup /path/to/last/backup.tar.gz
```

---

### Restore Fails

**Problem:** Restore script fails

**Solution:**
```bash
# Run with verbose output
./scripts/backup/restore-full.sh --backup /path/to/backup.tar.gz --verbose

# Check restore log
cat /tmp/restore-*.log
```

---

**Problem:** Services won't start after restore

**Solution:**
```bash
# Check service status
systemctl status pos-erp
systemctl status nginx

# Check logs
journalctl -u pos-erp -n 50
journalctl -u nginx -n 50

# Restart services
systemctl restart pos-erp
systemctl restart nginx
```

---

## Security Considerations

1. **Backup Encryption** — Consider encrypting backups for production
   ```bash
   # Encrypt backup
   gpg --encrypt --recipient your@email.com backup.tar.gz
   
   # Decrypt backup
   gpg --decrypt backup.tar.gz.gpg > backup.tar.gz
   ```

2. **Remote Storage** — Store backups off-site
   ```bash
   # Upload to S3
   aws s3 cp backup.tar.gz s3://your-bucket/backups/
   
   # Upload to Google Cloud
   gsutil cp backup.tar.gz gs://your-bucket/backups/
   ```

3. **Access Control** — Limit backup access
   ```bash
   # Set restrictive permissions
   chmod 600 /var/www/pos-erp-v6/backups/*.tar.gz
   ```

---

## Next Steps

- [01-server-setup.md](../migration/01-server-setup.md) — VPS provisioning
- [02-database-migration.md](../migration/02-database-migration.md) — Database migration
- [03-application-deploy.md](../migration/03-application-deploy.md) — Application deployment

---

**Last Updated:** 2026-06-04
