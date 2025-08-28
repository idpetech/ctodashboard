# 🚀 Quick AWS Permissions Fix (2 Methods)

## Method 1: AWS Console (Easiest - 3 minutes)

### Step 1: Add Managed Policies
1. Go to: https://console.aws.amazon.com/iam/
2. Users → `cli-admin-user` → Permissions tab
3. Click "Add permissions" → "Attach policies directly"
4. Search and attach:
   - ✅ `AmazonEC2ReadOnlyAccess` 
   - ✅ `AmazonRDSReadOnlyAccess`
5. Click "Next" → "Add permissions"

### Step 2: Add Lightsail Permissions (Custom Policy)
1. Still in IAM Console → Policies → "Create policy"
2. Click "JSON" tab
3. Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lightsail:GetInstances",
                "lightsail:GetBundles",
                "lightsail:GetRegions",
                "lightsail:GetInstanceState"
            ],
            "Resource": "*"
        }
    ]
}
```

4. Click "Next: Tags" → "Next: Review"
5. Name: `CTO-Dashboard-Lightsail-ReadOnly`
6. Click "Create policy"
7. Go back to Users → `cli-admin-user` → "Add permissions"
8. Attach your new `CTO-Dashboard-Lightsail-ReadOnly` policy

## Method 2: AWS CLI (Advanced - 1 minute)

```bash
# Add managed policies
aws iam attach-user-policy \
    --user-name cli-admin-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess

aws iam attach-user-policy \
    --user-name cli-admin-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonRDSReadOnlyAccess

# Create and attach Lightsail policy
aws iam create-policy \
    --policy-name CTO-Dashboard-Lightsail-ReadOnly \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "lightsail:GetInstances",
                "lightsail:GetBundles",
                "lightsail:GetRegions",
                "lightsail:GetInstanceState"
            ],
            "Resource": "*"
        }]
    }'

# Get your account ID for the policy ARN
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach the Lightsail policy
aws iam attach-user-policy \
    --user-name cli-admin-user \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/CTO-Dashboard-Lightsail-ReadOnly
```

## ✅ Test the Fix

After adding permissions (wait 1-2 minutes for propagation):

```bash
curl -s http://localhost:8000/assignments/ideptech/cto-insights
```

Look for these sections to now show data instead of errors:
- `lightsail_resources` should show `"total_instances": X`
- `ec2_resources` should show `"total_instances": X` 
- `rds_resources` should show `"total_databases": X`

## 🎯 What You'll Get

### Before (Permissions Errors):
```json
"lightsail_resources": {"error": "AccessDeniedException..."}
"ec2_resources": {"error": "UnauthorizedOperation..."}
"rds_resources": {"error": "AccessDenied..."}
```

### After (Detailed Insights):
```json
"lightsail_resources": {
    "total_instances": 1,
    "running_instances": 1,
    "instances": [{
        "name": "WordPress-1",
        "state": "running",
        "bundle_details": {
            "monthly_price": 3.5,
            "cpu_count": 1,
            "ram_size_gb": 0.5
        }
    }]
}
```

This will unlock the detailed Lightsail instance information that's likely consuming most of your $3.24 Lightsail costs!
