# GitHub connector setup guide

**Audience:** Non-technical operator who can follow web forms on GitHub.com and paste values into environment settings.

**Last updated:** 2026-06-18

---

## What you are setting up (in plain language)

CTOLens connects to GitHub using a **GitHub App** (not a personal access token, and not a “GitHub OAuth App” with a client secret).

There are **two separate jobs**:

1. **Platform setup (once per environment)** — You create a GitHub App on GitHub.com and put its credentials into CTOLens server settings (local file or Railway).
2. **Customer / workspace setup (per assignment)** — A user opens CTOLens, picks an assignment, and clicks **Connect GitHub App** to install the app on their organization.

---

## Key terms

| Term | What it means |
|------|----------------|
| **GitHub App** | An integration registered on GitHub. CTOLens uses this. |
| **OAuth App** | Different product on GitHub (Client ID + Client secret). **Do not use** for CTOLens GitHub connector. |
| **App ID** | A number GitHub assigns to your GitHub App. |
| **Slug** | The short name in the app URL: `github.com/apps/<slug>`. |
| **Private key** | A `.pem` file GitHub lets you download **once** when you generate a key. This replaces a “client secret.” |
| **Setup URL** | Where GitHub sends the user **after** they install the app. Must match your CTOLens URL. |
| **Installation** | When a customer approves the app on their org — done inside CTOLens UI, not in env vars. |

---

## One GitHub App per environment (recommended)

GitHub allows **one Setup URL per app**. Because local, staging, and production have **different URLs**, use **separate GitHub Apps**:

| Environment | Example CTOLens URL | Example GitHub App name | Example slug |
|-------------|---------------------|-------------------------|--------------|
| **Local** | `http://192.168.86.37:8520` or `http://localhost:8520` | CTOLens Dev | `ctolens-dev` |
| **Staging** | `https://web-staging-fad1.up.railway.app` | CTOLens Staging | `ctolens-staging` |
| **Production** | `https://your-production-domain.com` | CTOLens | `ctolens` |

The **slug is not “local” or your IP address**. It is whatever GitHub shows in the app’s URL on GitHub.com.

---

## Part A — Create the GitHub App (on GitHub.com)

Do this **once per environment** (start with Staging or Dev).

### Step 1 — Open the right place on GitHub

1. Log in to GitHub.
2. Click your **profile photo** (top right) → **Settings**.
3. Scroll down the left sidebar → **Developer settings**.
4. Click **GitHub Apps** (not “OAuth Apps”).
5. Click **New GitHub App**.

Direct link: https://github.com/settings/apps

### Step 2 — Fill in basic information

| Field | What to enter |
|-------|----------------|
| **GitHub App name** | e.g. `CTOLens Dev` (staging/prod: adjust name) |
| **Homepage URL** | Your CTOLens URL for this environment (see table above) |
| **Webhook** | Uncheck **Active** for initial setup (optional later) |

### Step 3 — Set the Setup URL (critical)

Find **Setup URL** (sometimes under “Post installation”).

Enter exactly:

```
<YOUR_CTOLENS_URL>/oauth/github/setup
```

Examples:

- Local: `http://192.168.86.37:8520/oauth/github/setup`
- Staging: `https://web-staging-fad1.up.railway.app/oauth/github/setup`
- Production: `https://your-production-domain.com/oauth/github/setup`

### Step 4 — Permissions (read-only)

Under **Repository permissions**, set read-only access as needed:

| Permission | Suggested level |
|------------|-----------------|
| Metadata | Read-only (required) |
| Contents | Read-only |
| Issues | Read-only (if tracking issues) |
| Pull requests | Read-only (if tracking PRs) |

Under **Organization permissions**, add read-only only if you need org-level data.

Click **Create GitHub App**.

### Step 5 — Collect three values from GitHub

On the app’s settings page:

#### 1) App ID

- Shown as **App ID** near the top (a number, e.g. `1234567`).
- Copy to: `GITHUB_APP_ID`

#### 2) Slug

- Open the app and look at the browser address bar:
  - `https://github.com/apps/ctolens-dev` → slug is `ctolens-dev`
- Copy to: `GITHUB_APP_SLUG`

#### 3) Private key

1. On the same page, find **Private keys**.
2. Click **Generate a private key**.
3. A `.pem` file downloads. **Store it safely** — GitHub will not show it again.
4. Copy the entire file contents into: `GITHUB_APP_PRIVATE_KEY`

**Tip for env files:** You can paste the key with `\n` between lines inside quotes, or use a multi-line value in Railway.

---

## Part B — Configure CTOLens (environment variables)

### Where to enter values

| Environment | Where |
|-------------|--------|
| **Local** | File: `.env.local` in the project folder (preferred over `.env` for secrets) |
| **Staging** | Railway → Staging service → **Variables** |
| **Production** | Railway → Production service → **Variables** |

**Never commit secrets to git.**

### Variables to set

```bash
# Turn on GitHub App connector + UI
ENABLE_GITHUB_APP_CONNECTOR=true
ENABLE_CONNECTOR_OAUTH_UI=true

# From GitHub App settings (Part A)
GITHUB_APP_ID=1234567
GITHUB_APP_SLUG=ctolens-dev
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# Your CTOLens public URL for THIS environment (no trailing slash)
APP_BASE_URL=http://192.168.86.37:8520
```

Optional flags:

```bash
PREFER_OAUTH_CONNECTORS=true
DISABLE_MANUAL_TOKENS=false
```

Set `DISABLE_MANUAL_TOKENS=true` only when you want to hide the legacy Personal Access Token tab.

### Restart after changes

| Environment | Action |
|-------------|--------|
| Local | Stop and restart `integrated_dashboard.py` |
| Staging / Production | Redeploy on Railway (or restart service) |

### Verify platform setup

Open in a browser (while logged in):

```
<YOUR_CTOLENS_URL>/api/feature-flags
```

Look for:

- `"github_oauth_ui": true`
- `"github_oauth_available": true`

If `github_oauth_available` is `false`, check `GITHUB_APP_ID` is set and the server was restarted.

---

## Part C — Connect GitHub inside CTOLens (workspace user)

This is done **in the app**, not in env vars.

1. Log in to CTOLens.
2. Open **Workspace Settings** or the dashboard **connector** modal for an assignment.
3. Choose **GitHub** → ensure **GitHub App** tab is selected (recommended).
4. Select the **assignment** from the dropdown.
5. Click **Connect GitHub App**.
6. GitHub opens → choose the **organization** → **Install**.
7. Return to CTOLens → enter **organization** (if needed) and **repositories to monitor** → **Save**.

Legacy option: **Personal Access Token** tab (not recommended for production).

---

## Environment cheat sheet

### Local

| Item | Value |
|------|--------|
| GitHub App | `CTOLens Dev` |
| `APP_BASE_URL` | `http://localhost:8520` or your LAN IP + port `8520` |
| Setup URL on GitHub | `{APP_BASE_URL}/oauth/github/setup` |
| Env file | `.env.local` |

### Staging

| Item | Value |
|------|--------|
| GitHub App | `CTOLens Staging` |
| `APP_BASE_URL` | `https://web-staging-fad1.up.railway.app` (your staging URL) |
| Setup URL on GitHub | `{APP_BASE_URL}/oauth/github/setup` |
| Env location | Railway Staging → Variables |

### Production

| Item | Value |
|------|--------|
| GitHub App | `CTOLens` |
| `APP_BASE_URL` | Your production domain |
| Setup URL on GitHub | `{APP_BASE_URL}/oauth/github/setup` |
| Env location | Railway Production → Variables |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| **Connect** button disabled | `GITHUB_APP_ID` missing | Set env vars and restart |
| GitHub page 404 after Connect | Wrong `GITHUB_APP_SLUG` | Match slug to `github.com/apps/<slug>` |
| 401 / login loop on Connect | Auth/session issue | Log in again; ensure Bearer token or session cookie works |
| After install, back to CTOLens fails | Setup URL mismatch | GitHub Setup URL must exactly match `{APP_BASE_URL}/oauth/github/setup` |
| You only have Client ID + Secret | Created **OAuth App** | Create a **GitHub App** instead |

---

## Checklist

**Platform admin (per environment)**

- [ ] GitHub App created under Developer settings → **GitHub Apps**
- [ ] Setup URL = `{APP_BASE_URL}/oauth/github/setup`
- [ ] App ID, slug, and private key copied
- [ ] Env vars set (`ENABLE_*`, `GITHUB_APP_*`, `APP_BASE_URL`)
- [ ] Server restarted / Railway redeployed
- [ ] `/api/feature-flags` shows `github_oauth_available: true`

**Workspace user (per assignment)**

- [ ] Assignment exists in CTOLens
- [ ] GitHub connector enabled for assignment
- [ ] **Connect GitHub App** completed on GitHub
- [ ] Repositories listed and credentials saved
