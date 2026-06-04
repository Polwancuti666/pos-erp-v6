# VPS Migration Guide — Beauty & Shine ERP

Complete guide for migrating the ERP system to a new VPS.

## Table of Contents

- [Overview](#overview)
- [Migration Checklist](#migration-checklist)
- [Documents](#documents)
- [Timeline](#timeline)
- [Rollback Plan](#rollback-plan)

---

## Overview

This folder contains all documentation needed to migrate Beauty & Shine ERP from the current server to a new VPS. The migration includes:

1. **Server provisioning** — OS setup, firewall, users
2. **Database migration** — SQLite data transfer
3. **Application deployment** — Backend + Frontend
4. **SSL/TLS setup** — HTTPS certificates
5. **DNS cutover** — Domain pointing
6. **CI/CD setup** — GitHub Actions secrets
7. **Monitoring** — Health checks, logging
8. **Verification** — Smoke tests, UAT

---

## Migration Checklist

### Pre-Migration (Day -3)
- [ ] Provision new VPS (Ubuntu 22.04 LTS)
- [ ] Verify VPS specs: 2 vCPU, 4GB RAM, 40GB SSD minimum
- [ ] Get SSH access to new VPS
- [ ] Backup current database
- [ ] Backup current `.env` file
- [ ] Note current DNS records
- [ ] Test SSH connectivity from local machine

### Migration Day (Day 0)
- [ ] Run `01-server-setup.sh` on new VPS
- [ ] Run `02-database-migration.sh` from old server
- [ ] Run `03-application-deploy.sh` on new VPS
- [ ] Run `04-ssl-setup.sh` on new VPS
- [ ] Verify application works via IP address
- [ ] Update DNS records to new VPS IP
- [ ] Wait for DNS propagation (5-30 minutes)
- [ ] Verify application works via domain name
- [ ] Setup GitHub Actions secrets
- [ ] Run smoke tests

### Post-Migration (Day +1)
- [ ] Monitor logs for 24 hours
- [ ] Verify all POS terminals can connect
- [ ] Verify backup cron is running
- [ ] Update documentation with new server details
- [ ] Decommission old server (after 7 days)

---

## Documents

| Document | Description |
|----------|-------------|
| [01-server-setup.md](./01-server-setup.md) | VPS provisioning, OS hardening, firewall |
| [02-database-migration.md](./02-database-migration.md) | SQLite backup, transfer, restore |
| [03-application-deploy.md](./03-application-deploy.md) | Backend + Frontend deployment |
| [04-ssl-setup.md](./04-ssl-setup.md) | Let's Encrypt SSL/TLS |
| [05-dns-cutover.md](./05-dns-cutover.md) | DNS records update |
| [06-github-secrets.md](./06-github-secrets.md) | CI/CD secrets setup |
| [07-monitoring.md](./07-monitoring.md) | Logs, health checks, alerts |
| [08-verification.md](./08-verification.md) | Smoke tests, UAT checklist |
| [scripts/](./scripts/) | Automated migration scripts |

---

## Timeline

```
Day -3:  Provision VPS, test connectivity
Day -1:  Full backup, dry-run migration
Day 0:   Migration execution (estimated 2-3 hours)
Day +1:  Monitoring, smoke tests
Day +7:  Decommission old server
```

---

## Rollback Plan

If migration fails:

1. **DNS rollback** — Revert DNS to old VPS IP
2. **Database rollback** — Restore from backup on old server
3. **Application rollback** — Old server still running
4. **Communication** — Notify team of rollback

**Estimated rollback time:** 15-30 minutes

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| Migration Lead | [Your Name] | [Your Contact] |
| DevOps | [Your Name] | [Your Contact] |
| Emergency | [Your Name] | [Your Contact] |

---

**Last Updated:** 2026-06-04
**Migration Version:** 1.0
