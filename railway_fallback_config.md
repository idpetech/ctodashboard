# Railway Database Connection Configuration

## Current Setup
- **Primary (Internal)**: `postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway?options=-csearch_path%3Dctodashboard`
- **Fallback (Public)**: `postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@acela.proxy.rlwy.net:48928/railway?options=-csearch_path%3Dctodashboard`

## If Internal URL Fails:

1. **Go to CTODashboard Railway project**
2. **Update DATABASE_URL variable to public URL**:
   ```
   postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@acela.proxy.rlwy.net:48928/railway?options=-csearch_path%3Dctodashboard
   ```
3. **Redeploy**

## Next Steps:

✅ **Ready to deploy Railway with PostgreSQL**
✅ **Post-deploy hook will create ctodashboard schema** 
✅ **Database adapter will automatically use PostgreSQL**
✅ **Fallback URL available if needed**