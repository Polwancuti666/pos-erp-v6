# Migration Quick Reference Card

Quick reference for the migration process. Print this and keep it handy during migration.

---

## Essential Commands

### SSH Access

```bash
# Old VPS
ssh root@OLD_VPS_IP

# New VPS
ssh root@NEW_VPS_IP

# With specific key
ssh -i ~/.ssh/github-actions-pos-erp root@NEW_VPS_IP
```

### Database Backup

```bash
# On old server
cd /var/www/pos-erp-v6
systemctl stop pos-erp
cp pos_erp.db backups/pos_erp_$(date +%Y%m%d_%H%M%S).db
sqlite3 backups/pos_erp_*.db "PRAGMA integrity_check;"
```

### Database Transfer

```bash
# From old server to new
scp /var/www/pos-erp-v6/backups/pos_erp_*.db root@NEW_VPS_IP:/var/www/pos-erp-v6/
```

### Application Restart

```bash
# On new server
systemctl restart pos-erp
systemctl status pos-erp
journalctl -u pos-erp -f
```

### Health Check

```bash
# Test API
curl http://localhost:8000/health

# Test via domain
curl https://beautynshine.web.id/health
```

### SSL Setup

```bash
# Install certificate
certbot --nginx -d beautynshine.web.id -d www.beautynshine.web.id

# Test renewal
certbot renew --dry-run
```

### DNS Check

```bash
# Check propagation
dig @8.8.8.8 beautynshine.web.id
dig @1.1.1.1 beautynshine.web.id

# Monitor
watch -n 10 'dig +short beautynshine.web.id'
```

---

## Emergency Contacts

| Role | Contact |
|------|---------|
| Migration Lead | [Your Name] |
| DevOps | [Your Name] |
| Emergency | [Your Name] |

---

## Rollback Steps

1. Revert DNS to old VPS IP
2. Start application on old server:
   ```bash
   ssh root@OLD_VPS_IP
   systemctl start pos-erp
   ```
3. Verify old server works
4. Investigate issue on new server

---

## Common Issues

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check `systemctl status pos-erp` |
| SSL Error | Run `certbot --nginx -d domain` |
| Database Locked | Kill hanging process: `lsof pos_erp.db` |
| Permission Denied | Fix: `chown -R deploy:deploy /var/www/pos-erp-v6` |
| DNS Not Propagating | Wait 5-30 min, check with `dig` |

---

## Migration Timeline

```
Day -3:  Provision VPS
Day -1:  Backup + dry-run
Day 0:   Migration (2-3 hours)
Day +1:  Monitoring
Day +7:  Decommission old server
```

---

## Checklist

### Pre-Migration
- [ ] Old server backed up
- [ ] .env file saved
- [ ] SSH access tested
- [ ] DNS TTL reduced to 300

### Migration
- [ ] Database transferred
- [ ] Application deployed
- [ ] SSL configured
- [ ] DNS updated

### Post-Migration
- [ ] Health check passed
- [ ] API tests passed
- [ ] Frontend tests passed
- [ ] Team notified

---

## Log Files

| Log | Location |
|-----|----------|
| Application | `journalctl -u pos-erp` |
| Nginx Access | `/var/www/pos-erp-v6/logs/nginx_access.log` |
| Nginx Error | `/var/www/pos-erp-v6/logs/nginx_error.log` |
| System | `/var/log/syslog` |
| Migration | `/tmp/migration-*.log` |

---

## File Locations

| File | Path |
|------|------|
| Application | `/var/www/pos-erp-v6` |
| Database | `/var/www/pos-erp-v6/pos_erp.db` |
| Environment | `/var/www/pos-erp-v6/.env` |
| Logs | `/var/www/pos-erp-v6/logs/` |
| Backups | `/var/www/pos-erp-v6/backups/` |
| Static Files | `/var/www/pos-erp-v6/static/` |
| Nginx Config | `/etc/nginx/sites-available/pos-erp` |
| Systemd Service | `/etc/systemd/system/pos-erp.service` |

---

**Print this page and keep it handy during migration!**
