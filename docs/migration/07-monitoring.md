# 07 — Monitoring

Complete guide for setting up monitoring and alerting for the ERP system.

## Overview

This guide covers:

1. Log monitoring
2. Health check endpoints
3. System resource monitoring
4. Application monitoring
5. Alerting setup

---

## Step 1: Log Monitoring

### Application Logs

```bash
# View real-time application logs
journalctl -u pos-erp -f

# View last 100 lines
journalctl -u pos-erp -n 100

# View logs since specific time
journalctl -u pos-erp --since "1 hour ago"

# View logs with specific priority
journalctl -u pos-erp -p err
```

### Nginx Logs

```bash
# Access logs
tail -f /var/www/pos-erp-v6/logs/nginx_access.log

# Error logs
tail -f /var/www/pos-erp-v6/logs/nginx_error.log

# Parse access logs for errors
awk '$9 >= 400' /var/www/pos-erp-v6/logs/nginx_access.log | tail -20
```

### System Logs

```bash
# System messages
journalctl -f

# Authentication logs
journalctl -f _COMM=sshd

# Kernel messages
dmesg | tail -20
```

---

## Step 2: Health Check Endpoints

### Application Health Check

Create a health check endpoint in your application:

```python
# In your FastAPI application
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": check_database_connection()
    }
```

### Test Health Endpoint

```bash
# Local test
curl http://localhost:8000/health

# Remote test
curl https://beautynshine.web.id/health

# Expected response:
# {"status": "ok", "version": "1.0.0", ...}
```

### Health Check Script

```bash
# Create health check script
cat > /var/www/pos-erp-v6/scripts/health-check.sh << 'SCRIPT'
#!/bin/bash
# Health check script

URL="http://localhost:8000/health"
EXPECTED_STATUS="ok"

# Check health endpoint
RESPONSE=$(curl -s "$URL")
STATUS=$(echo "$RESPONSE" | jq -r '.status')

if [ "$STATUS" = "$EXPECTED_STATUS" ]; then
    echo "[$(date)] ✓ Health check passed"
    exit 0
else
    echo "[$(date)] ✗ Health check failed"
    echo "Response: $RESPONSE"
    exit 1
fi
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/health-check.sh
```

---

## Step 3: System Resource Monitoring

### CPU and Memory

```bash
# Real-time system monitoring
htop

# CPU usage
mpstat 1 5

# Memory usage
free -h

# Process list
ps aux | head -20
```

### Disk Usage

```bash
# Disk usage
df -h

# Inode usage
df -i

# Large files
du -sh /* | sort -rh | head -10

# Specific directory
du -sh /var/www/pos-erp-v6/*
```

### Network

```bash
# Network connections
netstat -tulpn

# Active connections
ss -s

# Bandwidth usage
iftop
```

---

## Step 4: Application Monitoring

### Database Monitoring

```bash
# Database size
ls -lh /var/www/pos-erp-v6/pos_erp.db

# Database connections
sqlite3 /var/www/pos-erp-v6/pos_erp.db "PRAGMA journal_mode;"

# Query performance
time sqlite3 /var/www/pos-erp-v6/pos_erp.db "SELECT COUNT(*) FROM txn;"
```

### Process Monitoring

```bash
# Check if application is running
systemctl status pos-erp

# Check process resources
ps aux | grep pos_erp

# Check open files
lsof -p $(pgrep -f pos_erp)
```

---

## Step 5: Monitoring Scripts

### System Monitoring Script

```bash
# Create system monitoring script
cat > /var/www/pos-erp-v6/scripts/monitor-system.sh << 'SCRIPT'
#!/bin/bash
# System monitoring script

LOG_FILE="/var/www/pos-erp-v6/logs/system-monitor.log"

echo "=== System Monitor $(date) ===" >> "$LOG_FILE"

# CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
echo "CPU Usage: $CPU_USAGE%" >> "$LOG_FILE"

# Memory usage
MEM_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
echo "Memory Usage: $MEM_USAGE%" >> "$LOG_FILE"

# Disk usage
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}')
echo "Disk Usage: $DISK_USAGE" >> "$LOG_FILE"

# Load average
LOAD_AVG=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
echo "Load Average: $LOAD_AVG" >> "$LOG_FILE"

# Application status
APP_STATUS=$(systemctl is-active pos-erp)
echo "Application Status: $APP_STATUS" >> "$LOG_FILE"

# Nginx status
NGINX_STATUS=$(systemctl is-active nginx)
echo "Nginx Status: $NGINX_STATUS" >> "$LOG_FILE"

echo "=== End Monitor ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/monitor-system.sh

# Add to crontab (run every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /var/www/pos-erp-v6/scripts/monitor-system.sh") | crontab -
```

### Application Health Monitor

```bash
# Create application health monitor
cat > /var/www/pos-erp-v6/scripts/monitor-app.sh << 'SCRIPT'
#!/bin/bash
# Application health monitor

LOG_FILE="/var/www/pos-erp-v6/logs/app-monitor.log"
HEALTH_URL="http://localhost:8000/health"
MAX_RETRIES=3
RETRY_DELAY=5

echo "=== App Monitor $(date) ===" >> "$LOG_FILE"

# Check health endpoint
for i in $(seq 1 $MAX_RETRIES); do
    RESPONSE=$(curl -s -w "\n%{http_code}" "$HEALTH_URL" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        STATUS=$(echo "$BODY" | jq -r '.status' 2>/dev/null)
        if [ "$STATUS" = "ok" ]; then
            echo "✓ Health check passed (attempt $i)" >> "$LOG_FILE"
            exit 0
        fi
    fi
    
    echo "✗ Health check failed (attempt $i): HTTP $HTTP_CODE" >> "$LOG_FILE"
    
    if [ $i -lt $MAX_RETRIES ]; then
        sleep $RETRY_DELAY
    fi
done

# If all retries failed, restart application
echo "✗ All health checks failed, restarting application..." >> "$LOG_FILE"
systemctl restart pos-erp

# Wait for restart
sleep 10

# Check again
RESPONSE=$(curl -s -w "\n%{http_code}" "$HEALTH_URL" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Application restarted successfully" >> "$LOG_FILE"
else
    echo "✗ Application restart failed" >> "$LOG_FILE"
fi

echo "=== End Monitor ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/monitor-app.sh

# Add to crontab (run every minute)
(crontab -l 2>/dev/null; echo "* * * * * /var/www/pos-erp-v6/scripts/monitor-app.sh") | crontab -
```

---

## Step 6: Alerting Setup

### Email Alerts (Optional)

```bash
# Install mailutils
apt install -y mailutils

# Create alert script
cat > /var/www/pos-erp-v6/scripts/send-alert.sh << 'SCRIPT'
#!/bin/bash
# Send email alert

SUBJECT="$1"
BODY="$2"
EMAIL="admin@beautynshine.web.id"

echo "$BODY" | mail -s "[POS ERP ALERT] $SUBJECT" "$EMAIL"
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/send-alert.sh
```

### Slack Webhook (Optional)

```bash
# Create Slack alert script
cat > /var/www/pos-erp-v6/scripts/slack-alert.sh << 'SCRIPT'
#!/bin/bash
# Send Slack alert

WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"
MESSAGE="$1"

curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"$MESSAGE\"}" \
  "$WEBHOOK_URL"
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/slack-alert.sh
```

---

## Step 7: Log Rotation

```bash
# Verify logrotate is configured
cat /etc/logrotate.d/pos-erp

# Test logrotate
logrotate -d /etc/logrotate.d/pos-erp

# Force logrotate
logrotate -f /etc/logrotate.d/pos-erp
```

---

## Step 8: Monitoring Dashboard (Optional)

### Install Netdata (Lightweight Monitoring)

```bash
# Install Netdata
bash <(curl -Ss https://my-netdata.io/kickstart.sh)

# Access dashboard
# http://YOUR_VPS_IP:19999
```

### Install Glances (System Monitoring)

```bash
# Install Glances
pip install glances

# Run Glances
glances

# Web interface
glances -w
# http://YOUR_VPS_IP:61208
```

---

## Monitoring Checklist

- [ ] Application logs configured
- [ ] Nginx logs configured
- [ ] Health check endpoint working
- [ ] System monitoring script running
- [ ] Application health monitor running
- [ ] Log rotation configured
- [ ] Alerts configured (email/Slack)
- [ ] Monitoring dashboard accessible

---

## Common Alerts

### Application Down

```bash
# Alert when application is not responding
if ! curl -s http://localhost:8000/health > /dev/null; then
    /var/www/pos-erp-v6/scripts/send-alert.sh \
        "Application Down" \
        "POS ERP application is not responding"
fi
```

### High CPU Usage

```bash
# Alert when CPU usage > 90%
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d. -f1)
if [ "$CPU_USAGE" -gt 90 ]; then
    /var/www/pos-erp-v6/scripts/send-alert.sh \
        "High CPU Usage" \
        "CPU usage is at $CPU_USAGE%"
fi
```

### Low Disk Space

```bash
# Alert when disk usage > 90%
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    /var/www/pos-erp-v6/scripts/send-alert.sh \
        "Low Disk Space" \
        "Disk usage is at $DISK_USAGE%"
fi
```

---

## Next Steps

After monitoring is set up:

1. [08-verification.md](./08-verification.md) — Run verification tests

---

**Estimated Time:** 30-45 minutes
