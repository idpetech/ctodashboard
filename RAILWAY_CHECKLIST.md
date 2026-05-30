# 🚄 Railway SQLite Database Deployment Checklist

## ✅ Pre-Deployment Steps

### 1. Set Environment Variables
```bash
# Run this script to set all required variables
./railway_setup.sh

# Or set manually:
railway variables set CREDENTIAL_MASTER_KEY="your-64-char-key"
railway variables set JWT_SECRET="your-32-char-key"
railway variables set DATABASE_URL="sqlite:///config/secure_credentials.db"
railway variables set FLASK_ENV="production"
railway variables set FLASK_DEBUG="false"
```

### 2. Verify Volume Configuration
- ✅ `railway.json` includes volume mount for `/app/config`
- ✅ Database will persist across deployments
- ✅ Volume name: `database-storage`

### 3. Database Initialization
- ✅ `railway_init_db.py` runs on each deployment (release command)
- ✅ Creates database if it doesn't exist
- ✅ Sets up initial admin user if needed

## 🚀 Deployment Process

### 1. Deploy to Railway
```bash
git push origin master  # Auto-deploys via GitHub integration
# OR
railway up              # Direct deployment
```

### 2. Monitor Deployment
```bash
# Watch deployment logs
railway logs

# Check specific logs
railway logs --filter "database"
railway logs --filter "health"
```

## 🔍 Post-Deployment Verification

### 1. Health Checks
Visit these URLs after deployment:

**Basic Health:**
- `https://your-app.railway.app/health`
- Should return `{"status": "healthy"}`

**Database Health:**
- `https://your-app.railway.app/admin/db/health`
- Should show database connected, encryption available

**Database Status Page:**
- `https://your-app.railway.app/admin/db/status`
- Visual dashboard of database status

**Audit Logs:**
- `https://your-app.railway.app/admin/db/audit`
- Shows recent database activity (non-sensitive)

### 2. Database Verification Commands
```bash
# SSH into Railway container (if needed)
railway shell

# Check database file exists
ls -la /app/config/secure_credentials.db

# Check permissions
ls -la /app/config/

# Test database connectivity
python -c "from services.security.secure_database import secure_db; print(secure_db.health_check())"
```

## 🛠️ Troubleshooting

### Common Issues & Solutions

#### ❌ "Database not found"
**Solution:**
```bash
# Check volume is mounted
railway logs | grep "config"

# Verify environment variables
railway variables
```

#### ❌ "Master key not configured"
**Solution:**
```bash
# Set the master key
railway variables set CREDENTIAL_MASTER_KEY="your-key"

# Restart deployment
railway up
```

#### ❌ "Permission denied"
**Solution:**
```bash
# Check volume permissions in Railway dashboard
# Ensure /app/config is writable

# Check Railway logs for permission errors
railway logs --filter "permission"
```

#### ❌ "Foreign key constraint failed"
**Solution:**
```bash
# Database schema mismatch - run initialization
railway run python railway_init_db.py
```

## 📊 Monitoring & Maintenance

### Regular Health Checks
Set up monitoring for these endpoints:
- `/health` - Application health
- `/admin/db/health` - Database health
- `/admin/db/status` - Visual status dashboard

### Log Monitoring
```bash
# Monitor application logs
railway logs --follow

# Filter for database-related issues
railway logs --filter "database|credential|error" --follow

# Check initialization logs
railway logs --filter "railway_init_db"
```

### Database Backup Strategy
```bash
# Export user data (for backup)
railway run python -c "
from services.security.secure_database import secure_db
health = secure_db.health_check()
print('Database stats:', health.get('statistics'))
"

# Note: Actual credential backup requires master key
```

## 🚨 Emergency Procedures

### Database Recovery
If database is corrupted or lost:

1. **Check volume status in Railway dashboard**
2. **Verify backup availability**
3. **Re-run initialization:**
   ```bash
   railway run python railway_init_db.py
   ```

### Master Key Rotation
If master key needs to be changed:

1. **Backup current database** (while old key still works)
2. **Generate new master key**
3. **Update Railway environment variable**
4. **Re-encrypt all credentials** (requires migration script)

### Performance Issues
If SQLite performance is slow:

1. **Check database size:**
   ```bash
   railway shell
   ls -lh /app/config/secure_credentials.db
   ```

2. **Consider database maintenance:**
   ```bash
   railway run python -c "
   import sqlite3
   conn = sqlite3.connect('/app/config/secure_credentials.db')
   conn.execute('VACUUM;')
   conn.close()
   "
   ```

## ✅ Success Criteria

Deployment is successful when:

- [ ] `/health` returns 200 OK
- [ ] `/admin/db/health` shows all systems healthy
- [ ] `/admin/db/status` displays correct statistics
- [ ] Database file exists at `/app/config/secure_credentials.db`
- [ ] Environment variables are properly set
- [ ] No error logs related to database connectivity
- [ ] User authentication works (if users exist)
- [ ] Audit logs show activity

## 🔗 Useful Railway Commands

```bash
# Deploy and watch logs
railway up --detach && railway logs --follow

# Check environment variables
railway variables

# Connect to database (if needed)
railway shell
sqlite3 /app/config/secure_credentials.db ".tables"

# Restart deployment
railway redeploy

# Check resource usage
railway status
```