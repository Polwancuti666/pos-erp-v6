# 03 — Application Deployment

Complete guide for deploying the application on the new VPS.

## Overview

This guide covers:

1. Cloning the repository
2. Setting up Python environment
3. Building the frontend
4. Configuring systemd service
5. Setting up Nginx reverse proxy

---

## Step 1: Clone Repository

```bash
# Switch to deploy user
su - deploy

# Navigate to application directory
cd /var/www/pos-erp-v6

# Clone repository
git clone https://github.com/Polwancuti666/pos-erp-v6.git .

# Or if already cloned, pull latest
git pull origin main

# Verify
git status
git log --oneline -3
```

---

## Step 2: Setup Python Environment

```bash
# Navigate to project directory
cd /var/www/pos-erp-v6

# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Install production dependencies
pip install gunicorn uvicorn[standard]

# Verify installation
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
```

---

## Step 3: Configure Environment Variables

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with production values
nano .env
```

### Required Environment Variables:

```bash
# Application
POS_ERP_ENV=production
POS_ERP_SECRET_KEY=<generate-with-openssl-rand-hex-32>
POS_ERP_HOST=0.0.0.0
POS_ERP_PORT=8000

# Database
POS_ERP_DB_PATH=/var/www/pos-erp-v6/pos_erp.db

# Security
POS_ERP_CORS_ORIGINS=https://beautynshine.web.id,https://www.beautynshine.web.id
POS_ERP_ALLOWED_HOSTS=beautynshine.web.id,www.beautynshine.web.id

# Branch
POS_ERP_DEFAULT_BRANCH=HQ
```

### Generate Secret Key:

```bash
# Generate a secure secret key
openssl rand -hex 32
```

---

## Step 4: Build Frontend

```bash
# Navigate to frontend directory
cd /var/www/pos-erp-v6/frontend

# Install dependencies
npm ci

# Build for production
npm run build

# Verify build output
ls -la dist/

# Copy to static directory
mkdir -p /var/www/pos-erp-v6/static
cp -r dist/* /var/www/pos-erp-v6/static/

# Set permissions
chmod -R 755 /var/www/pos-erp-v6/static
```

---

## Step 5: Test Application

```bash
# Navigate to project root
cd /var/www/pos-erp-v6

# Activate virtual environment
source .venv/bin/activate

# Test run
python -m pos_erp.main

# In another terminal, test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Stop test run (Ctrl+C)
```

---

## Step 6: Create Systemd Service

```bash
# Exit to root user
exit

# Create systemd service file
cat > /etc/systemd/system/pos-erp.service << 'EOF'
[Unit]
Description=Beauty & Shine POS ERP API
Documentation=https://github.com/Polwancuti666/pos-erp-v6
After=network.target

[Service]
Type=exec
User=deploy
Group=deploy
WorkingDirectory=/var/www/pos-erp-v6
Environment="PATH=/var/www/pos-erp-v6/.venv/bin:/usr/bin"
EnvironmentFile=/var/www/pos-erp-v6/.env
ExecStart=/var/www/pos-erp-v6/.venv/bin/gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --timeout 120 \
  --access-logfile /var/www/pos-erp-v6/logs/access.log \
  --error-logfile /var/www/pos-erp-v6/logs/error.log \
  pos_erp.main:app
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/www/pos-erp-v6
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable pos-erp

# Start service
systemctl start pos-erp

# Check status
systemctl status pos-erp

# View logs
journalctl -u pos-erp -f
```

---

## Step 7: Configure Nginx

```bash
# Create Nginx configuration
cat > /etc/nginx/sites-available/pos-erp << 'EOF'
# Upstream for load balancing (if needed)
upstream pos_erp_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name beautynshine.web.id www.beautynshine.web.id;

    # Allow ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name beautynshine.web.id www.beautynshine.web.id;

    # SSL certificates (will be configured in Step 04-ssl-setup.md)
    ssl_certificate /etc/letsencrypt/live/beautynshine.web.id/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/beautynshine.web.id/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml+rss application/atom+xml image/svg+xml;

    # Static files (frontend)
    root /var/www/pos-erp-v6/static;
    index index.html;

    # Frontend routes (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://pos_erp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://pos_erp_backend;
        proxy_set_header Host $host;
        access_log off;
    }

    # WebSocket support (if needed)
    location /ws/ {
        proxy_pass http://pos_erp_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~* \.(db|sqlite|sql|bak|backup|log)$ {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Client max body size
    client_max_body_size 50M;

    # Logging
    access_log /var/www/pos-erp-v6/logs/nginx_access.log;
    error_log /var/www/pos-erp-v6/logs/nginx_error.log;
}
EOF

# Create certbot directory
mkdir -p /var/www/certbot

# Enable site
ln -sf /etc/nginx/sites-available/pos-erp /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test configuration
nginx -t

# Reload Nginx
systemctl reload nginx
```

---

## Step 8: Create Log Rotation

```bash
# Create logrotate configuration
cat > /etc/logrotate.d/pos-erp << 'EOF'
/var/www/pos-erp-v6/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 deploy deploy
    sharedscripts
    postrotate
        systemctl reload pos-erp > /dev/null 2>&1 || true
    endscript
}
EOF

# Test logrotate
logrotate -d /etc/logrotate.d/pos-erp
```

---

## Step 9: Create Backup Script

```bash
# Create backup script
cat > /var/www/pos-erp-v6/scripts/backup.sh << 'SCRIPT'
#!/bin/bash
# Daily database backup

BACKUP_DIR="/var/www/pos-erp-v6/backups"
DB_PATH="/var/www/pos-erp-v6/pos_erp.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/pos_erp_${TIMESTAMP}.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
cp "$DB_PATH" "$BACKUP_FILE"

# Compress
gzip "$BACKUP_FILE"

# Keep only last 30 days
find "$BACKUP_DIR" -name "pos_erp_*.db.gz" -mtime +30 -delete

echo "Backup created: ${BACKUP_FILE}.gz"
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/backup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /var/www/pos-erp-v6/scripts/backup.sh >> /var/www/pos-erp-v6/logs/backup.log 2>&1") | crontab -
```

---

## Verification

```bash
# Run verification script
cat > /tmp/verify_deployment.sh << 'SCRIPT'
#!/bin/bash
echo "=== Deployment Verification ==="
echo ""

# Check systemd service
echo "1. Systemd Service:"
if systemctl is-active pos-erp > /dev/null 2>&1; then
    echo "   ✓ pos-erp service: ACTIVE"
else
    echo "   ✗ pos-erp service: INACTIVE"
fi

# Check Nginx
echo ""
echo "2. Nginx:"
if systemctl is-active nginx > /dev/null 2>&1; then
    echo "   ✓ Nginx: ACTIVE"
else
    echo "   ✗ Nginx: INACTIVE"
fi

# Check API health
echo ""
echo "3. API Health:"
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if echo "$HEALTH" | grep -q "ok"; then
    echo "   ✓ API health: OK"
else
    echo "   ✗ API health: FAILED"
fi

# Check static files
echo ""
echo "4. Static Files:"
if [ -f /var/www/pos-erp-v6/static/index.html ]; then
    echo "   ✓ Frontend built: YES"
else
    echo "   ✗ Frontend built: NO"
fi

# Check database
echo ""
echo "5. Database:"
if [ -f /var/www/pos-erp-v6/pos_erp.db ]; then
    SIZE=$(ls -lh /var/www/pos-erp-v6/pos_erp.db | awk '{print $5}')
    echo "   ✓ Database exists: $SIZE"
else
    echo "   ✗ Database: NOT FOUND"
fi

# Check logs
echo ""
echo "6. Logs:"
if [ -d /var/www/pos-erp-v6/logs ]; then
    echo "   ✓ Log directory exists"
    ls -la /var/www/pos-erp-v6/logs/
else
    echo "   ✗ Log directory: NOT FOUND"
fi

echo ""
echo "=== Verification Complete ==="
SCRIPT

chmod +x /tmp/verify_deployment.sh
/tmp/verify_deployment.sh
```

---

## Next Steps

After application deployment is complete:

1. [04-ssl-setup.md](./04-ssl-setup.md) — Setup SSL/TLS
2. [05-dns-cutover.md](./05-dns-cutover.md) — Update DNS records

---

**Estimated Time:** 30-45 minutes
