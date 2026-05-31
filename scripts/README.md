# Database Management Scripts

## Manual Database Operations

### Initial Database Setup
```bash
# Only run when setting up database for the first time
python scripts/db_init_manual.py
```

### Database Migration
```bash
# For schema changes and updates
python scripts/db_migrate.py
```

### Database Health Check
```bash
# Check database status without making changes
python scripts/db_health_check.py
```

## When to Use Each Script

### `db_init_manual.py`
- First deployment to new environment
- Complete database reset (destructive)
- Setting up local development environment

### `db_migrate.py` (Future)
- Schema changes
- Adding new tables/columns
- Data transformations
- Non-destructive updates

### `db_health_check.py` (Future)
- Verify database connectivity
- Check data integrity
- Monitor performance metrics
- Troubleshooting

## Safety Guidelines

1. **Always backup** before running migration scripts
2. **Test migrations** in staging environment first
3. **Never run** init scripts on production with existing data
4. **Monitor logs** during and after migration
5. **Have rollback plan** for schema changes

## Railway Deployment

Database initialization is now **manual only**. 

To initialize database on Railway:
```bash
railway run python scripts/db_init_manual.py
```

This prevents accidental database resets on every deployment.