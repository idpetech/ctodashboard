# AWS connector setup guide

**Audience:** Non-technical operator coordinating between CTOLens platform settings and a customer’s AWS account.

**Last updated:** 2026-06-18

---

## What you are setting up

CTOLens reads AWS data (costs, resources, etc.) using a **cross-account IAM role** — the **recommended** method.

- The **customer** deploys a read-only IAM role in **their** AWS account (via CloudFormation).
- **CTOLens** assumes that role temporarily — **no long-lived AWS access keys** from the customer.

There are two roles:

| Role | Responsibility |
|------|----------------|
| **CTOLens platform admin** | Enable feature flags; set CTOLens’s own AWS account ID (and optional STS credentials) in env vars |
| **Customer / workspace user** | Download template, deploy stack in customer AWS, paste Role ARN into CTOLens |

Legacy: **Access Key ID + Secret** tab in the UI (not recommended for enterprise).

---

## Key terms

| Term | Meaning |
|------|---------|
| **CTOLens AWS Account ID** | The AWS account where CTOLens runs (platform account) — customers trust this account |
| **Customer AWS Account** | Where the customer deploys the read-only role |
| **External ID** | A secret string that must match in IAM and CTOLens — prevents confused deputy attacks |
| **Role ARN** | Amazon Resource Name of the role CTOLens will assume |
| **CloudFormation stack** | One-click template the customer deploys to create the role |
| **STS** | AWS “temporary credentials” service CTOLens uses to assume the role |

---

## Part A — Platform setup (CTOLens admin, per environment)

### Step 1 — Enable feature flags

Set in `.env.local` (local) or Railway Variables (staging/production):

```bash
ENABLE_AWS_CROSS_ACCOUNT_ROLE=true
ENABLE_AWS_ROLE_CONNECTOR_UI=true
DISABLE_AWS_ACCESS_KEYS=false
```

Set `DISABLE_AWS_ACCESS_KEYS=true` only when you want to hide legacy access-key fields.

### Step 2 — Set CTOLens platform AWS account ID

```bash
CTOLENS_AWS_ACCOUNT_ID=123456789012
```

This is the **12-digit AWS account ID** of the account that runs CTOLens (or the account whose IAM user/role will call `sts:AssumeRole`).

**How to find it:** AWS Console → top-right account menu → **Account ID**.

Use the correct account ID **per environment** if staging and production run in different AWS accounts.

### Step 3 — Platform credentials for STS (usually required on Railway)

CTOLens needs permission to call AWS STS `AssumeRole` into customer accounts:

```bash
CTOLENS_AWS_ACCESS_KEY_ID=AKIA...
CTOLENS_AWS_SECRET_ACCESS_KEY=...
```

Create a dedicated IAM user or role in the **platform** AWS account with a minimal policy allowing `sts:AssumeRole` on customer role ARNs (or broader during pilot).

**Local dev:** If these are unset, boto3 may use your default AWS CLI profile — only for developer machines.

### Step 4 — Optional prefix for External IDs

```bash
CTOLENS_AWS_EXTERNAL_ID_PREFIX=ctolens
```

External IDs are auto-generated per workspace + assignment, e.g. `ctolens-admin_workspace-ilsa`.

### Restart / redeploy

Restart local Flask or redeploy Railway after changing variables.

### Verify platform setup

Open:

```
<YOUR_CTOLENS_URL>/api/feature-flags
```

Look for:

- `"aws_role_onboarding_available": true`
- `"ctolens_aws_account_id": "123456789012"`

---

## Part B — Customer onboarding (in CTOLens UI)

Done **per assignment** in Workspace Settings or the AWS connector modal.

### Step 1 — Open AWS connector

1. Log in to CTOLens.
2. Open connector configuration for an **assignment**.
3. Use the **cross-account IAM role** / enterprise onboarding section (not legacy access keys).

### Step 2 — Load onboarding values

1. Select the **assignment** in the dropdown.
2. Click **Load External ID** (or similar onboarding button).
3. Note these values (also shown in UI):

| Value | Used for |
|-------|----------|
| **CTOLens AWS Account ID** | CloudFormation parameter `CTOLensAccountId` |
| **External ID** | CloudFormation parameter `ExternalId` |

### Step 3 — Download CloudFormation template

Click **Download CloudFormation Template** or open:

```
<YOUR_CTOLENS_URL>/api/cloud-access/aws/cloudformation-template
```

File: `ctolens-readonly-role.yaml`

### Step 4 — Deploy in customer AWS account

Customer AWS admin:

1. Log in to **AWS Console** → **CloudFormation** → **Create stack** → **Upload template**.
2. Upload `ctolens-readonly-role.yaml`.
3. Enter parameters:

| Parameter | Value |
|-----------|--------|
| **CTOLensAccountId** | From CTOLens UI (platform account ID) |
| **ExternalId** | From CTOLens UI (exact copy — case sensitive) |
| **RoleName** | Default `CTOLensReadOnlyRole` (or agreed name) |

4. Acknowledge IAM capabilities → **Create stack**.
5. Wait for stack status **CREATE_COMPLETE**.
6. Open **Outputs** tab → copy **RoleArn** (and note customer **Account ID**).

### Step 5 — Register role in CTOLens

Back in CTOLens AWS form:

| Field | Value |
|-------|--------|
| **Role ARN** | From CloudFormation output |
| **AWS Account ID** | Customer’s 12-digit account ID |
| **External ID** | Same value used in the stack |
| **Region** | e.g. `us-east-1` |

Click **Test Connection** → **Save Credentials**.

---

## Environment cheat sheet

### Local

| Item | Guidance |
|------|----------|
| Env file | `.env.local` |
| `APP_BASE_URL` | `http://localhost:8520` or LAN URL |
| `CTOLENS_AWS_ACCOUNT_ID` | Dev platform AWS account (or shared staging account) |
| Customer testing | Use a **sandbox AWS account**, not production customer data |

### Staging

| Item | Guidance |
|------|----------|
| Env | Railway Staging Variables |
| `CTOLENS_AWS_ACCOUNT_ID` | AWS account used by staging CTOLens deployment |
| Customers | Test orgs deploy stack to their **non-prod** AWS accounts |

### Production

| Item | Guidance |
|------|----------|
| Env | Railway Production Variables |
| `CTOLENS_AWS_ACCOUNT_ID` | Production platform AWS account |
| Customers | Each customer deploys stack in **their** production AWS account |

**Important:** External ID and Role ARN are **per assignment**. Each assignment gets its own External ID when you click **Load External ID**.

---

## What the CloudFormation template creates

- IAM role (default name: `CTOLensReadOnlyRole`)
- Read-only policy (Cost Explorer, EC2 describe, CloudWatch, S3 list, etc.)
- Trust policy allowing **only** the CTOLens platform account to assume the role, with the **External ID** condition

Customers do **not** share access keys with CTOLens.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| Onboarding UI hidden | Flags off or missing `CTOLENS_AWS_ACCOUNT_ID` | Set env vars; restart |
| AssumeRole denied | Wrong External ID or Account ID | Must match CloudFormation parameters exactly |
| AssumeRole denied | Wrong `CTOLENS_AWS_ACCOUNT_ID` on server | Platform env must match trusted account in template |
| Test connection fails | Stack not complete or wrong Role ARN | Verify stack CREATE_COMPLETE and copy ARN from Outputs |
| No cost data | Cost Explorer not enabled in customer account | Enable Cost Explorer in AWS Billing |

---

## Checklist

**CTOLens platform admin (per environment)**

- [ ] `ENABLE_AWS_CROSS_ACCOUNT_ROLE=true`
- [ ] `ENABLE_AWS_ROLE_CONNECTOR_UI=true`
- [ ] `CTOLENS_AWS_ACCOUNT_ID` set (12 digits)
- [ ] `CTOLENS_AWS_ACCESS_KEY_ID` / `CTOLENS_AWS_SECRET_ACCESS_KEY` set on Railway
- [ ] Feature flags show `aws_role_onboarding_available: true`

**Customer / workspace user (per assignment)**

- [ ] Assignment selected in CTOLens
- [ ] External ID loaded from CTOLens
- [ ] CloudFormation stack deployed successfully
- [ ] Role ARN + Account ID + External ID entered in CTOLens
- [ ] Test connection passes
- [ ] Credentials saved

---

## Security notes (for operators)

- Never put customer **secret access keys** in CTOLens if role-based access is available.
- Treat **External ID** as sensitive — do not share across assignments.
- Use separate AWS sandbox accounts for local/staging tests.
