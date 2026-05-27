# Deployment Guide

## POS-ERP Integration Engine V6

---

## 1. Docker Compose Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: pos-erp-db
    environment:
      POSTGRES_DB: pos_erp
      POSTGRES_USER: pos_erp
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pos_erp"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pos-erp-api
    ports:
      - "8000:8000"
    environment:
      - PG_HOST=postgres
      - PG_PORT=5432
      - PG_DATABASE=pos_erp
      - PG_USER=pos_erp
      - PG_PASSWORD=${PG_PASSWORD}
      - APP_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  postgres_data:
```

### Starting the Stack

```bash
# Create .env file with required variables
cp .env.example .env
# Edit .env with production values

# Start services
docker compose up -d

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

---

## 2. Environment Variables

### Required Variables

| Variable | Description | Example |
|---|---|---|
| `PG_PASSWORD` | PostgreSQL password | `secure_password_here` |
| `SECRET_KEY` | Application secret key | `random-64-char-hex-string` |
| `ENCRYPTION_KEY` | Data encryption key | `random-32-byte-hex` |

### Database Configuration

| Variable | Description | Default |
|---|---|---|
| `PG_HOST` | PostgreSQL host | `localhost` |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_DATABASE` | Database name | `pos_erp` |
| `PG_USER` | Database user | `pos_erp` |
| `PG_PASSWORD` | Database password | (required) |
| `PG_SSLMODE` | SSL mode | `prefer` |

### Application Configuration

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | Environment | `development` |
| `APP_DEBUG` | Debug mode | `false` |
| `APP_PORT` | Server port | `8000` |
| `APP_HOST` | Server host | `0.0.0.0` |

### Payment Provider Configuration

| Variable | Description | Default |
|---|---|---|
| `BCA_VA_MERCHANT_ID` | BCA VA merchant ID | (required for BCA) |
| `BCA_VA_API_KEY` | BCA VA API key | (required for BCA) |
| `BCA_VA_SECRET_KEY` | BCA VA secret key | (required for BCA) |
| `MIDTRANS_MERCHANT_ID` | Midtrans merchant ID | (required for Midtrans) |
| `MIDTRANS_CLIENT_KEY` | Midtrans client key | (required for Midtrans) |
| `MIDTRANS_SERVER_KEY` | Midtrans server key | (required for Midtrans) |

### Sync Configuration

| Variable | Description | Default |
|---|---|---|
| `SYNC_INTERVAL_SECONDS` | Sync check interval | `60` |
| `SYNC_MAX_RETRIES` | Max retry attempts | `3` |
| `ERP_API_URL` | ERP API endpoint | (required) |
| `ERP_API_KEY` | ERP API key | (required) |

### Security Configuration

| Variable | Description | Default |
|---|---|---|
| `RATE_LIMIT_REQUESTS` | Requests per window | `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` |
| `STAFF_LOCK_TIMEOUT_MINUTES` | Lock timeout | `10` |

### .env.example

```env
# Database
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=pos_erp
PG_USER=pos_erp
PG_PASSWORD=change_me_in_production
PG_SSLMODE=prefer

# Application
APP_ENV=development
APP_DEBUG=true
APP_PORT=8000
SECRET_KEY=change_me_to_random_64_chars
ENCRYPTION_KEY=change_me_to_random_32_bytes_hex

# Payment Providers (configure as needed)
# BCA_VA_MERCHANT_ID=
# BCA_VA_API_KEY=
# BCA_VA_SECRET_KEY=
# MIDTRANS_MERCHANT_ID=
# MIDTRANS_CLIENT_KEY=
# MIDTRANS_SERVER_KEY=

# ERP Integration
# ERP_API_URL=
# ERP_API_KEY=

# Sync
SYNC_INTERVAL_SECONDS=60
SYNC_MAX_RETRIES=3

# Security
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
STAFF_LOCK_TIMEOUT_MINUTES=10
```

---

## 3. Cloudflare Tunnel Configuration

### Overview

Cloudflare Tunnel provides secure ingress without exposing ports directly to the internet.

### Setup

1. **Install cloudflared**:
```bash
# Docker image includes cloudflared
# Or install separately:
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

2. **Authenticate**:
```bash
cloudflared tunnel login
```

3. **Create tunnel**:
```bash
cloudflared tunnel create pos-erp
```

4. **Configure tunnel** (`~/.cloudflared/config.yml`):
```yaml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: pos.beautynshine.web.id
    service: http://api:8000
  - service: http_status:404
```

5. **Run tunnel**:
```bash
cloudflared tunnel run pos-erp
```

### Docker Compose with Tunnel

```yaml
services:
  # ... postgres and api services ...

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: pos-erp-tunnel
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    restart: unless-stopped
    depends_on:
      - api
```

### DNS Configuration

| Record | Type | Value |
|---|---|---|
| pos.beautynshine.web.id | CNAME | <tunnel-id>.cfargotunnel.com |

---

## 4. Health Checks

### Application Health

```bash
# Basic health check
curl http://localhost:8000/health

# Expected response:
# {"status": "ok", "service": "pos-erp-v6"}
```

### Database Health

```bash
# PostgreSQL health check
docker exec pos-erp-db pg_isready -U pos_erp

# Connection test
docker exec pos-erp-db psql -U pos_erp -d pos_erp -c "SELECT 1;"
```

### Docker Health Status

```bash
# Check all container health
docker compose ps

# View health check logs
docker inspect --format='{{json .State.Health}}' pos-erp-api
```

---

## 5. Production Checklist

### Pre-Deployment

- [ ] All environment variables configured
- [ ] Strong passwords for PG_PASSWORD, SECRET_KEY, ENCRYPTION_KEY
- [ ] Payment provider credentials configured (if applicable)
- [ ] ERP API credentials configured (if applicable)
- [ ] Cloudflare Tunnel configured
- [ ] DNS records created

### Security

- [ ] APP_DEBUG=false
- [ ] PG_SSLMODE=require (for remote PostgreSQL)
- [ ] Rate limiting configured
- [ ] CORS origins restricted
- [ ] Security headers enabled

### Monitoring

- [ ] Health check endpoint accessible
- [ ] Log aggregation configured
- [ ] Alerting for failed health checks
- [ ] Exception queue monitoring

### Backup

- [ ] PostgreSQL backup strategy configured
- [ ] Backup retention policy defined
- [ ] Restore procedure documented and tested

---

## 6. Scaling Considerations

### Current Architecture

Single-instance deployment suitable for:
- 1-5 POS terminals
- Single branch location
- < 1000 transactions/day

### Scaling Options (Planned)

| Component | Current | Scaled |
|---|---|---|
| API Server | Single instance | Multiple behind load balancer |
| Database | Single PostgreSQL | Primary + read replicas |
| Sync | Single worker | Multiple workers with queue |

---

## 7. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|---|---|---|
| API won't start | Missing env vars | Check .env file |
| Database connection failed | PostgreSQL not ready | Wait for health check |
| Sync not working | ERP API unreachable | Check ERP_API_URL |
| Payment callbacks failing | Tunnel not running | Restart cloudflared |
| High memory usage | In-memory repository | Switch to PostgreSQL |

### Log Locations

```bash
# API logs
docker compose logs api

# PostgreSQL logs
docker compose logs postgres

# Tunnel logs
docker compose logs cloudflared
```

### Debug Mode

```bash
# Enable debug logging
export APP_DEBUG=true
export APP_ENV=development

# Restart API
docker compose restart api
```
