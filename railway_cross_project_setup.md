# Railway Cross-Project Database Setup

## Issue
Database PostgreSQL instance is in **different Railway project** from CTODashboard app.

## Railway Network Access Options

### Option 1: Public Database URL
```bash
# Get public connection string from Railway PostgreSQL project
# Format: postgresql://user:pass@external-host:port/db
DATABASE_URL="postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@<public-host>:5432/railway?options=-csearch_path%3Dctodashboard"
```

### Option 2: Railway Private Networking
```bash
# If projects are in same team, use private networking
# Need to enable Railway's private networking feature
DATABASE_URL="postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@<private-network-host>:5432/railway?options=-csearch_path%3Dctodashboard"
```

### Option 3: Environment Variable Reference
```json
{
  "variables": {
    "DATABASE_URL": "${{PostgreSQL.DATABASE_URL}}?options=-csearch_path%3Dctodashboard"
  }
}
```

## Recommended Approach

1. **Get actual DATABASE_URL from PostgreSQL Railway project**
2. **Add ctodashboard schema suffix**: `?options=-csearch_path%3Dctodashboard`
3. **Use full external URL instead of internal**

## Steps to Fix

1. Go to PostgreSQL Railway project dashboard
2. Copy the **public** DATABASE_URL (not internal)
3. Append schema parameter
4. Update railway.json with correct URL
5. Deploy and test connection

## Example Final URL
```
postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@roundhouse.proxy.rlwy.net:12345/railway?options=-csearch_path%3Dctodashboard
```

Where `roundhouse.proxy.rlwy.net:12345` is the public Railway proxy endpoint.