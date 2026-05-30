# GitHub Token Requirements for CTO Dashboard

## 🔍 Debugging Results

The GitHub token validation system is working correctly. The validation function properly:
- Makes authenticated requests to GitHub's API
- Handles 401 responses correctly (invalid/expired tokens)
- Provides clear error messages
- Tests network connectivity

## 📋 GitHub Token Requirements

To work with the CTO Dashboard, your GitHub Personal Access Token must:

### 1. Token Type
- **Personal Access Token (Classic)** - recommended for this application
- OR **Fine-grained Personal Access Token** (new GitHub tokens)

### 2. Required Scopes (for Classic tokens)
- **`repo`** - Full control of private repositories
- **`read:org`** - Read organization membership (optional but recommended)
- **`read:user`** - Read user profile information

### 3. Token Format
- Classic tokens: 40 characters, typically start with `ghp_`
- Should look like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 🛠️ How to Create a Valid Token

1. **Go to GitHub Settings**
   - Visit: https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"

2. **Configure Token**
   - **Note**: "CTO Dashboard API Access"
   - **Expiration**: Choose based on your needs (30/60/90 days or custom)
   - **Scopes**: Select at minimum:
     - ✅ `repo` (Full control of private repositories)
     - ✅ `read:user` (Read user profile information)
     - ✅ `read:org` (Read organization membership) - optional

3. **Generate and Copy**
   - Click "Generate token"
   - **Important**: Copy the token immediately - you won't see it again!

## 🔧 Testing Your Token

Use the debug tool to test your token:
```bash
cd /Users/haseebtoor/Projects/ctodashboard
source venv/bin/activate
python debug_github.py YOUR_TOKEN_HERE
```

## ❌ Common Issues

### "Invalid GitHub token or expired"
- **Cause**: Token is literally invalid, expired, or revoked
- **Solution**: Generate a new token following the steps above

### "GitHub token lacks required permissions" 
- **Cause**: Token doesn't have `repo` scope
- **Solution**: Recreate token with proper scopes

### Token appears valid but still fails
- **Check expiration**: Tokens can expire (check GitHub settings)
- **Check revocation**: Token may have been revoked
- **Check format**: Ensure you copied the full token
- **Check network**: Ensure you can reach api.github.com

## 🧪 Manual Verification

You can test your token manually:
```bash
curl -H "Authorization: token YOUR_TOKEN_HERE" https://api.github.com/user
```

**Expected response for valid token:**
```json
{
  "login": "your-username",
  "id": 12345,
  "name": "Your Name",
  ...
}
```

**Response for invalid token:**
```json
{
  "message": "Bad credentials",
  "documentation_url": "https://docs.github.com/rest"
}
```