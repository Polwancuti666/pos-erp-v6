# 04 — SSL/TLS Setup

Complete guide for setting up HTTPS with Let's Encrypt.

## Overview

This guide covers:

1. Installing Certbot
2. Obtaining SSL certificate
3. Configuring Nginx for HTTPS
4. Setting up auto-renewal
5. Testing SSL configuration

---

## Step 1: Install Certbot

```bash
# Install Certbot and Nginx plugin
apt install -y certbot python3-certbot-nginx

# Verify installation
certbot --version
```

---

## Step 2: Obtain SSL Certificate

```bash
# Make sure Nginx is running and configured
systemctl status nginx

# Obtain certificate
certbot --nginx \
  -d beautynshine.web.id \
  -d www.beautynshine.web.id \
  --non-interactive \
  --agree-tos \
  --email admin@beautynshine.web.id \
  --redirect

# Verify certificate
certbot certificates
```

---

## Step 3: Verify Nginx Configuration

Certbot automatically modifies the Nginx configuration. Verify it:

```bash
# Test Nginx configuration
nginx -t

# Reload Nginx
systemctl reload nginx

# Check Nginx status
systemctl status nginx
```

### Expected Nginx Config:

After Certbot runs, your Nginx config should have:

```nginx
server {
    listen 443 ssl http2;
    server_name beautynshine.web.id www.beautynshine.web.id;

    ssl_certificate /etc/letsencrypt/live/beautynshine.web.id/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/beautynshine.web.id/privkey.pem;

    # ... rest of configuration
}

server {
    listen 80;
    server_name beautynshine.web.id www.beautynshine.web.id;

    # Certbot challenge location
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}
```

---

## Step 4: Setup Auto-Renewal

Let's Encrypt certificates expire every 90 days. Setup auto-renewal:

```bash
# Test renewal process (dry run)
certbot renew --dry-run

# Certbot installs a systemd timer by default
systemctl list-timers | grep certbot

# Verify timer is active
systemctl status certbot.timer

# If timer is not active, enable it
systemctl enable certbot.timer
systemctl start certbot.timer
```

### Manual Renewal Script (Optional)

```bash
# Create renewal script
cat > /var/www/pos-erp-v6/scripts/renew-ssl.sh << 'SCRIPT'
#!/bin/bash
# SSL certificate renewal script

echo "=== SSL Certificate Renewal ==="
echo "Date: $(date)"

# Renew certificates
certbot renew --quiet

# Reload Nginx to pick up new certificates
systemctl reload nginx

# Check certificate expiry
echo ""
echo "Certificate expiry:"
certbot certificates | grep "Expiry Date"

echo ""
echo "=== Renewal Complete ==="
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/renew-ssl.sh

# Add to crontab (run monthly)
(crontab -l 2>/dev/null; echo "0 3 1 * * /var/www/pos-erp-v6/scripts/renew-ssl.sh >> /var/www/pos-erp-v6/logs/ssl-renewal.log 2>&1") | crontab -
```

---

## Step 5: Test SSL Configuration

### Test HTTPS Access

```bash
# Test local access
curl -I https://beautynshine.web.id

# Expected output:
# HTTP/2 200
# strict-transport-security: max-age=63072000; includeSubDomains; preload
# x-frame-options: SAMEORIGIN
# x-content-type-options: nosniff
```

### Test SSL Labs Rating

Visit: https://www.ssllabs.com/ssltest/analyze.html?d=beautynshine.web.id

Expected rating: **A+**

### Test Security Headers

```bash
# Test security headers
curl -s -I https://beautynshine.web.id | grep -i "strict-transport\|x-frame\|x-content-type\|x-xss"

# Expected output:
# strict-transport-security: max-age=63072000; includeSubDomains; preload
# x-frame-options: SAMEORIGIN
# x-content-type-options: nosniff
# x-xss-protection: 1; mode=block
```

### Test HTTP to HTTPS Redirect

```bash
# Test HTTP redirect
curl -I http://beautynshine.web.id

# Expected output:
# HTTP/1.1 301 Moved Permanently
# Location: https://beautynshine.web.id/
```

### Test Certificate Chain

```bash
# Test certificate chain
openssl s_client -connect beautynshine.web.id:443 -servername beautynshine.web.id < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Expected output:
# notBefore=...
# notAfter=...  (should be ~90 days from now)
```

---

## Step 6: Configure SSL Parameters (Optional but Recommended)

```bash
# Create SSL parameters snippet
cat > /etc/nginx/snippets/ssl-params.conf << 'EOF'
# SSL protocols
ssl_protocols TLSv1.2 TLSv1.3;

# SSL ciphers
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

# Prefer server ciphers
ssl_prefer_server_ciphers off;

# SSL session
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Diffie-Hellman parameters
ssl_dhparam /etc/nginx/dhparam.pem;
EOF

# Generate Diffie-Hellman parameters (takes a few minutes)
openssl dhparam -out /etc/nginx/dhparam.pem 2048

# Include snippet in Nginx config
# Add this line in the server block:
# include /etc/nginx/snippets/ssl-params.conf;
```

---

## Troubleshooting

### Certificate Not Found

```bash
# Check if certificate exists
ls -la /etc/letsencrypt/live/beautynshine.web.id/

# If not, request new certificate
certbot --nginx -d beautynshine.web.id -d www.beautynshine.web.id
```

### Certificate Expired

```bash
# Force renewal
certbot renew --force-renewal

# Reload Nginx
systemctl reload nginx
```

### Nginx Won't Start After SSL Setup

```bash
# Check Nginx configuration
nginx -t

# Check error logs
tail -f /var/log/nginx/error.log

# Common issues:
# - Certificate file not found
# - Port 443 already in use
# - Syntax error in config
```

### Mixed Content Warnings

```bash
# Check for HTTP resources on HTTPS pages
curl -s https://beautynshine.web.id | grep -i "http://"

# Update any hardcoded HTTP URLs to HTTPS
```

---

## Security Checklist

- [ ] SSL certificate installed and valid
- [ ] HTTP to HTTPS redirect working
- [ ] HSTS header present
- [ ] Security headers configured
- [ ] Auto-renewal enabled
- [ ] SSL Labs rating A or A+
- [ ] No mixed content warnings

---

## Next Steps

After SSL setup is complete:

1. [05-dns-cutover.md](./05-dns-cutover.md) — Update DNS records
2. [06-github-secrets.md](./06-github-secrets.md) — Setup CI/CD secrets

---

**Estimated Time:** 15-30 minutes
