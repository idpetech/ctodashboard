# Jira connector setup guide

**Audience:** Non-technical operator who can use the Atlassian Developer site and paste values into environment settings.

**Last updated:** 2026-06-18

---

## What you are setting up

CTOLens connects to **Jira Cloud** using **Atlassian OAuth 2.0 (3LO)** — the customer clicks **Connect Jira** and signs in with Atlassian.

Two jobs:

1. **Platform setup (once per environment)** — Create an OAuth 2.0 app in Atlassian Developer Console; put Client ID and Secret into CTOLens env vars.
2. **Workspace setup (per assignment)** — User selects assignment → **Connect Jira** → approves access → adds project keys in CTOLens.

**Note:** Jira **API tokens** (email + token) are the **legacy** path in the UI. OAuth is recommended.

---

## Key terms

| Term | Meaning |
|------|---------|
| **Client ID** | Public identifier for your Atlassian OAuth app |
| **Client secret** | Secret password for your OAuth app — store in env vars only |
| **Callback URL** | Where Atlassian sends the user after they approve access |
| **Scopes** | What CTOLens is allowed to read in Jira (read-only) |
| **Cloud ID** | Atlassian internal site ID — stored automatically after connect |

---

## One Atlassian OAuth app per environment (recommended)

Each environment has a different callback URL, so use **separate OAuth apps**:

| Environment | Example CTOLens URL | Example app name |
|-------------|---------------------|------------------|
| **Local** | `http://192.168.86.37:8520` | CTOLens Dev |
| **Staging** | `https://web-staging-fad1.up.railway.app` | CTOLens Staging |
| **Production** | `https://your-production-domain.com` | CTOLens |

---

## Part A — Create the Atlassian OAuth app

### Step 1 — Open Atlassian Developer Console

1. Go to: https://developer.atlassian.com/console/myapps/
2. Log in with your Atlassian account.
3. Click **Create** → **OAuth 2.0 integration**.

### Step 2 — Name the app

| Field | Example |
|-------|---------|
| **App name** | `CTOLens Dev` / `CTOLens Staging` / `CTOLens` |

### Step 3 — Set permissions (scopes)

Enable **read-only** Jira access. CTOLens default scopes:

```
read:jira-work read:jira-user offline_access
```

In the developer UI, grant equivalent **Jira API** read permissions (issues, users, offline refresh).

`offline_access` allows CTOLens to refresh tokens without asking the user to log in every time.

### Step 4 — Set the Callback URL (critical)

In **Authorization** / **Callback URL**, enter **exactly one URL per app**:

```
<YOUR_CTOLENS_URL>/oauth/jira/callback
```

Examples:

- Local: `http://192.168.86.37:8520/oauth/jira/callback`
- Staging: `https://web-staging-fad1.up.railway.app/oauth/jira/callback`
- Production: `https://your-production-domain.com/oauth/jira/callback`

Save the app.

### Step 5 — Copy Client ID and Secret

On the app’s **Settings** page:

| Atlassian field | CTOLens env var |
|-----------------|-----------------|
| Client ID | `JIRA_OAUTH_CLIENT_ID` |
| Client secret | `JIRA_OAUTH_CLIENT_SECRET` |

Copy the secret immediately if Atlassian only shows it once.

---

## Part B — Configure CTOLens (environment variables)

### Where to enter values

| Environment | Where |
|-------------|--------|
| **Local** | `.env.local` |
| **Staging** | Railway → Staging → **Variables** |
| **Production** | Railway → Production → **Variables** |

### Variables to set

```bash
ENABLE_JIRA_OAUTH_CONNECTOR=true
ENABLE_CONNECTOR_OAUTH_UI=true

JIRA_OAUTH_CLIENT_ID=your-client-id-from-atlassian
JIRA_OAUTH_CLIENT_SECRET=your-client-secret-from-atlassian

APP_BASE_URL=http://192.168.86.37:8520
```

Optional (defaults are usually fine):

```bash
JIRA_OAUTH_SCOPES=read:jira-work read:jira-user offline_access
PREFER_OAUTH_CONNECTORS=true
DISABLE_MANUAL_TOKENS=false
```

Restart the server / redeploy Railway after changes.

### Verify platform setup

Open:

```
<YOUR_CTOLENS_URL>/api/feature-flags
```

Confirm:

- `"jira_oauth_ui": true`
- `"jira_oauth_available": true`

---

## Part C — Connect Jira inside CTOLens (workspace user)

1. Log in to CTOLens.
2. Open connector settings for an **assignment**.
3. Choose **Jira** → **Atlassian OAuth** tab (recommended).
4. Select the **assignment** in the dropdown.
5. Click **Connect Jira**.
6. Atlassian login/consent screen → approve.
7. You return to CTOLens Workspace Settings with a success message.
8. Enter **project keys** to monitor (e.g. `PROJ,ENG`) → **Save**.

Legacy tab: **API Token** — requires Jira site URL, email, and API token from https://id.atlassian.com/manage-profile/security/api-tokens

---

## Environment cheat sheet

### Local

| Item | Value |
|------|--------|
| Atlassian app | `CTOLens Dev` |
| Callback URL | `http://<host>:8520/oauth/jira/callback` |
| `APP_BASE_URL` | Same as host (no trailing slash) |
| Env file | `.env.local` |

### Staging

| Item | Value |
|------|--------|
| Atlassian app | `CTOLens Staging` |
| Callback URL | `https://<staging-domain>/oauth/jira/callback` |
| Env | Railway Staging Variables |

### Production

| Item | Value |
|------|--------|
| Atlassian app | `CTOLens` |
| Callback URL | `https://<prod-domain>/oauth/jira/callback` |
| Env | Railway Production Variables |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| **Connect Jira** disabled | Missing `JIRA_OAUTH_CLIENT_ID` | Set env vars; restart |
| Redirect error from Atlassian | Callback URL mismatch | Must match `{APP_BASE_URL}/oauth/jira/callback` exactly |
| Connected but no data | Project keys wrong | Enter correct Jira project keys (e.g. `ABC`) |
| Token expired errors | Missing `offline_access` scope | Add scope in Atlassian app + env `JIRA_OAUTH_SCOPES` |

---

## Checklist

**Platform admin (per environment)**

- [ ] Atlassian OAuth 2.0 app created
- [ ] Callback URL = `{APP_BASE_URL}/oauth/jira/callback`
- [ ] Read scopes + offline_access configured
- [ ] Client ID and secret in env vars
- [ ] `ENABLE_JIRA_OAUTH_CONNECTOR` and `ENABLE_CONNECTOR_OAUTH_UI` = true
- [ ] Server restarted; `jira_oauth_available: true` in feature flags

**Workspace user (per assignment)**

- [ ] Assignment selected
- [ ] **Connect Jira** completed
- [ ] Project keys saved
- [ ] Test connection succeeds
