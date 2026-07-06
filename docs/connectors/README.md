# Connector setup guides

Step-by-step guides for non-technical operators and admins. Each connector uses **one integration per environment** (local, staging, production).

| Guide | Who configures the external site | Who configures CTOLens env vars | Who connects in the UI |
|-------|----------------------------------|--------------------------------|------------------------|
| [GitHub](./GITHUB-CONNECTOR-SETUP.md) | Platform admin (GitHub.com) | Platform admin | Workspace user per assignment |
| [Jira](./JIRA-CONNECTOR-SETUP.md) | Platform admin (Atlassian) | Platform admin | Workspace user per assignment |
| [AWS](./AWS-CONNECTOR-SETUP.md) | Customer AWS admin + platform admin | Platform admin | Customer / workspace user per assignment |

**Important:** Platform secrets (App IDs, private keys, client secrets) are **never** entered in the dashboard UI. They go in environment variables only (`.env.local` locally, Railway **Variables** on staging/production).
