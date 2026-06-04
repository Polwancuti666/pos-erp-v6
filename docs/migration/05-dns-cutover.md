# 05 — DNS Cutover

Complete guide for updating DNS records to point to the new VPS.

## Overview

This guide covers:

1. Documenting current DNS records
2. Updating DNS records
3. Verifying DNS propagation
4. Testing the new server

---

## Step 1: Document Current DNS Records

Before making any changes, document all current DNS records:

```bash
# Check current DNS records
dig beautynshine.web.id A
dig beautynshine.web.id AAAA
dig www.beautynshine.web.id CNAME
dig beautynshine.web.id MX
dig beautynshine.web.id TXT

# Or use nslookup
nslookup beautynshine.web.id
nslookup -type=MX beautynshine.web.id
nslookup -type=TXT beautynshine.web.id
```

### Save Current Records:

Create a backup of current DNS settings:

```bash
cat > /tmp/dns-backup-$(date +%Y%m%d).txt << 'EOF'
=== Current DNS Records ===
Date: $(date)
Domain: beautynshine.web.id

A Records:
- beautynshine.web.id → OLD_VPS_IP (TTL: 300)

CNAME Records:
- www.beautynshine.web.id → beautynshine.web.id

MX Records:
- (if any)

TXT Records:
- (if any, includes SPF, DKIM, etc.)

Nameservers:
- ns1.example.com
- ns2.example.com
EOF
```

---

## Step 2: Update DNS Records

### Option A: Cloudflare (If using Cloudflare)

1. Login to Cloudflare dashboard
2. Select your domain
3. Go to DNS → Records
4. Update the following:

| Type | Name | Content | TTL | Proxy |
|------|------|---------|-----|-------|
| A | @ | NEW_VPS_IP | Auto | Proxied |
| A | www | NEW_VPS_IP | Auto | Proxied |

5. Save changes

### Option B: Other DNS Providers

Update the following records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | NEW_VPS_IP | 300 |
| A | www | NEW_VPS_IP | 300 |

**Note:** Set TTL to 300 (5 minutes) before migration for faster propagation.

### Option C: Direct Domain Registrar

If using registrar's DNS (e.g., GoDaddy, Namecheap):

1. Login to registrar dashboard
2. Find DNS management section
3. Update A records:
   - `@` → NEW_VPS_IP
   - `www` → NEW_VPS_IP
4. Save changes

---

## Step 3: Verify DNS Propagation

DNS changes can take 5 minutes to 48 hours to propagate globally.

### Check Propagation Status:

```bash
# Check from multiple DNS servers

# Google DNS
dig @8.8.8.8 beautynshine.web.id A

# Cloudflare DNS
dig @1.1.1.1 beautynshine.web.id A

# OpenDNS
dig @208.67.222.222 beautynshine.web.id A

# Local DNS
dig beautynshine.web.id A

# Expected output: NEW_VPS_IP
```

### Online Propagation Checkers:

- https://dnschecker.org/
- https://whatsmydns.net/
- https://www.dnsmap.io/

### Command Line Monitoring:

```bash
# Monitor DNS propagation
watch -n 10 'dig +short beautynshine.web.id'

# Or use this script
cat > /tmp/check-dns.sh << 'SCRIPT'
#!/bin/bash
DOMAIN="beautynshine.web.id"
EXPECTED_IP="NEW_VPS_IP"

echo "Checking DNS propagation for $DOMAIN..."
echo "Expected IP: $EXPECTED_IP"
echo ""

while true; do
    CURRENT_IP=$(dig +short $DOMAIN | head -1)
    TIMESTAMP=$(date +"%H:%M:%S")
    
    if [ "$CURRENT_IP" = "$EXPECTED_IP" ]; then
        echo "[$TIMESTAMP] ✓ DNS propagated: $CURRENT_IP"
        break
    else
        echo "[$TIMESTAMP] ✗ Waiting... Current: $CURRENT_IP"
    fi
    
    sleep 10
done
SCRIPT

chmod +x /tmp/check-dns.sh
/tmp/check-dns.sh
```

---

## Step 4: Test New Server

Once DNS has propagated:

### Test HTTP Access

```bash
# Test HTTP redirect
curl -I http://beautynshine.web.id

# Expected: 301 redirect to HTTPS
```

### Test HTTPS Access

```bash
# Test HTTPS
curl -I https://beautynshine.web.id

# Expected: 200 OK
```

### Test API Endpoint

```bash
# Test API health
curl https://beautynshine.web.id/health

# Expected: {"status": "ok", ...}
```

### Test from Browser

1. Open browser
2. Visit https://beautynshine.web.id
3. Check for SSL certificate (lock icon)
4. Test POS login: https://beautynshine.web.id/pos
5. Test Admin login: https://beautynshine.web.id/login

---

## Step 5: Update Cloudflare Settings (If Using Cloudflare)

If using Cloudflare, update these settings:

### SSL/TLS Settings

1. Go to SSL/TLS → Overview
2. Set encryption mode to **Full (strict)**
3. Enable **Always Use HTTPS**
4. Enable **HSTS** (with max-age: 6 months)

### Page Rules (Optional)

Create page rules for better performance:

1. `*beautynshine.web.id/api/*`
   - Cache Level: Bypass
   - Security Level: High

2. `*beautynshine.web.id/static/*`
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month

### Firewall Rules (Optional)

Block malicious traffic:

1. Go to Security → WAF
2. Create rule: Block countries (if needed)
3. Create rule: Rate limit login attempts

---

## Step 6: Monitor for Issues

After DNS cutover, monitor for:

### Check Server Logs

```bash
# Monitor Nginx access logs
tail -f /var/www/pos-erp-v6/logs/nginx_access.log

# Monitor Nginx error logs
tail -f /var/www/pos-erp-v6/logs/nginx_error.log

# Monitor application logs
journalctl -u pos-erp -f
```

### Common Issues

1. **SSL Certificate Errors**
   - Verify certificate is for correct domain
   - Check certificate chain is complete

2. **502 Bad Gateway**
   - Check if application is running
   - Check Nginx proxy configuration

3. **Slow Loading**
   - Check server resources (CPU, RAM)
   - Check database performance

4. **Mixed Content Warnings**
   - Update any hardcoded HTTP URLs
   - Check for external resources

---

## Rollback Plan

If issues occur after DNS cutover:

### Immediate Rollback

```bash
# Revert DNS records to old VPS IP
# Update A records:
# - @ → OLD_VPS_IP
# - www → OLD_VPS_IP

# Wait for propagation (5-30 minutes)
# Monitor with: watch -n 10 'dig +short beautynshine.web.id'
```

### Verify Rollback

```bash
# Check DNS reverted
dig @8.8.8.8 beautynshine.web.id A
# Should show: OLD_VPS_IP

# Test old server
curl -I https://beautynshine.web.id
# Should work on old server
```

---

## Checklist

- [ ] Current DNS records documented
- [ ] DNS records updated to new VPS IP
- [ ] TTL set to 300 before migration
- [ ] DNS propagation verified (all regions)
- [ ] HTTP access working
- [ ] HTTPS access working
- [ ] API endpoints responding
- [ ] POS login working
- [ ] Admin login working
- [ ] SSL certificate valid
- [ ] No mixed content warnings
- [ ] Server logs clean
- [ ] Rollback plan documented

---

## Next Steps

After DNS cutover is complete:

1. [06-github-secrets.md](./06-github-secrets.md) — Setup CI/CD secrets
2. [07-monitoring.md](./07-monitoring.md) — Setup monitoring
3. [08-verification.md](./08-verification.md) — Run verification tests

---

**Estimated Time:** 30-60 minutes (including propagation wait)
