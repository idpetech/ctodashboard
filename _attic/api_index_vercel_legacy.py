# Legacy Vercel deployment file - ARCHIVED
# 
# This file was originally created for Vercel serverless deployment but is no longer used.
# Current deployment uses Railway with railway.json pointing to integrated_dashboard:app
# 
# Original purpose: Vercel serverless function entry point
# Archived during Phase 6 consolidation to remove blocker for integrated_dashboard.py cleanup
# Date archived: $(date)
#
# Original content below:
# ================

from integrated_dashboard import app

# Vercel serverless function entry point
def handler(request):
    return app(request.environ, lambda x, y: None)
