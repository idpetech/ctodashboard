# API Token Setup Guide

This guide walks through getting API tokens for each service to see real metrics in your CTO Dashboard.

## 🔑 Required API Tokens

### 1. GitHub Personal Access Token

**Steps:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Set expiration to 90 days
4. Select scopes:
   - ✅ `repo` (for repository access)
   - ✅ `read:org` (for organization data)
   - ✅ `read:user` (for user information)
5. Click "Generate token"
6. Copy the token (starts with `ghp_`)

**Add to backend/.env:**
```
GITHUB_TOKEN=ghp_your_actual_token_here
GITHUB_ORG=your-github-username-or-org
```

### 2. Jira API Token

**Steps:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label like "CTO Dashboard"
4. Copy the token

**Add to backend/.env:**
```
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_TOKEN=your_actual_jira_token_here
```

### 3. AWS Cost Explorer Access

**Steps:**
1. Go to AWS IAM Console
2. Create new user "cto-dashboard-readonly"
3. Attach policy: `AWSCostExplorerFullAccess` (or create custom readonly policy)
4. Create access key
5. Copy Access Key ID and Secret

**Add to backend/.env:**
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

### 4. Railway API Token

**Steps:**
1. Go to https://railway.app/account/tokens
2. Click "Create New Token"
3. Give it a name like "CTO Dashboard"
4. Copy the token

**Add to backend/.env:**
```
RAILWAY_TOKEN=your_railway_token
RAILWAY_PROJECT_ID=your_project_id_from_railway_dashboard
```

## 🧪 Test Your Configuration

After adding tokens, restart the backend and test:

```bash
cd backend
source .venv/bin/activate
python main.py &

# Test health check shows services configured
curl http://localhost:8000/health

# Test live metrics
curl http://localhost:8000/assignments/ideptech/metrics
```

## 🔒 Security Notes

- ✅ Never commit `.env` files to git
- ✅ Use minimum required permissions for each token
- ✅ Set token expiration dates
- ✅ Rotate tokens periodically
- ✅ Different tokens for dev/staging/production

## 🚀 Quick Test Setup

**Want to test without real tokens? Add mock tokens:**

```bash
# backend/.env
GITHUB_TOKEN=test_token
GITHUB_ORG=test-org
JIRA_URL=https://test.atlassian.net
JIRA_EMAIL=test@example.com
JIRA_TOKEN=test_token
```

The dashboard will show error messages for invalid tokens, but you can see the UI working.