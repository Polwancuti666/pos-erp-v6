# Troubleshooting Guide

## Database Connection Issues

### `connection refused` or `could not connect to server`

```bash
# Check PostgreSQL is running
systemctl status postgresql

# Check connection parameters
psql -h localhost -U erp -d pos_erp

# Verify .env settings match your PostgreSQL config
cat .env | grep POSTGRES
```

### `database "pos_erp" does not exist`

```bash
createdb -U erp pos_erp
```

### `permission denied for database`

```bash
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE pos_erp TO erp;"
```

## Port Conflicts

### `Address already in use: port 8000`

```bash
# Find what's using the port
lsof -i :8000

# Kill the process
kill <PID>

# Or use a different port
uvicorn pos_erp.fastapi_app:app --port 8001
```

## JWT / Authentication Issues

### `Invalid token` or `Token expired`

- Check `POS_ERP_SECRET_KEY` is set in `.env`
- Token expiry is controlled by `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- Clear localStorage in browser and re-login

### `CORS error` in browser console

```bash
# Add your frontend URL to CORS_ORIGINS in .env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://yourdomain.com
```

## Frontend Build Errors

### `npm install` fails

```bash
rm -rf node_modules package-lock.json
npm install
```

### TypeScript errors after pulling new code

```bash
npx tsc --noEmit  # See all type errors
npm run build     # Build will show errors
```

## Migration Issues

### `relation "xxx" does not exist`

The database schema is auto-created on startup. If tables are missing:

```bash
# Restart the backend to trigger schema creation
uvicorn pos_erp.fastapi_app:app --host 0.0.0.0 --port 8000
```

### `column "xxx" does not exist`

Pull latest code and restart. Schema changes are applied automatically.

## Cloudflare Tunnel

### Tunnel not connecting

```bash
# Check tunnel status
cloudflared tunnel info <tunnel-name>

# Verify token
cat .env | grep CLOUDFLARE

# Restart tunnel
cloudflared tunnel run
```

## Performance

### Slow API responses

Check database indexes:

```bash
psql -U erp -d pos_erp -c "\di"  # List indexes
```

Run the index migration:

```bash
python scripts/apply_indexes.py
```

## Getting Help

1. Check the [API Reference](api-reference.md)
2. Review [Architecture](system-architecture.md)
3. Open a [GitHub Issue](https://github.com/your-org/pos-erp-v6/issues)
