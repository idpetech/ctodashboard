# 🕵️ Find Your Hidden Lightsail Costs

## 🚨 **Problem**: You're paying $3.24/month for Lightsail with 0 instances

This is usually caused by "invisible" Lightsail resources like static IPs, snapshots, or load balancers.

## 🔍 **Investigation Methods**

### Method 1: AWS Console (Visual - Easiest)

1. **Go to Lightsail Console**: https://lightsail.aws.amazon.com/
2. **Check ALL these sections**:
   - ✅ **Instances** (you already know this is 0)
   - ❗ **Static IPs** ← Most likely culprit ($3.60/month each when unattached)
   - ❗ **Load balancers** ← $18/month each
   - ❗ **Databases** ← $15+/month each
   - ❗ **Snapshots** ← $0.05/GB/month
   - ❗ **Containers** ← Variable pricing
   - ❗ **Storage (Block storage)** ← $0.10/GB/month

3. **Check OTHER AWS REGIONS**:
   - Switch region dropdown (top right)
   - Check: **N. Virginia, Ohio, Oregon, Ireland** (most common)

### Method 2: AWS CLI (Comprehensive)

```bash
# Check all Lightsail resources across regions
echo "🔍 Checking Lightsail resources in all regions..."

# List of major regions
REGIONS=("us-east-1" "us-west-2" "us-east-2" "eu-west-1" "ap-southeast-1")

for region in "${REGIONS[@]}"; do
    echo "📍 Region: $region"
    
    # Static IPs (most common hidden cost)
    echo "  💰 Static IPs:"
    aws lightsail get-static-ips --region $region --query 'staticIps[].{Name:name,IP:ipAddress,AttachedTo:attachedTo}' --output table 2>/dev/null || echo "    (no access or none found)"
    
    # Load balancers
    echo "  ⚖️ Load Balancers:"
    aws lightsail get-load-balancers --region $region --query 'loadBalancers[].name' --output text 2>/dev/null || echo "    (no access or none found)"
    
    # Databases
    echo "  🗄️ Databases:"
    aws lightsail get-relational-databases --region $region --query 'relationalDatabases[].name' --output text 2>/dev/null || echo "    (no access or none found)"
    
    # Snapshots
    echo "  📸 Snapshots:"
    aws lightsail get-instance-snapshots --region $region --query 'instanceSnapshots[].{Name:name,Size:sizeInGb}' --output table 2>/dev/null || echo "    (no access or none found)"
    
    echo ""
done
```

### Method 3: Cost Explorer Deep Dive

1. **AWS Cost Explorer**: https://console.aws.amazon.com/cost-management/home
2. Click **"Cost Explorer"** → **"Launch Cost Explorer"**
3. **Filter by**:
   - Service: Amazon Lightsail
   - Time: Last month
4. **Group by**: Usage Type
5. This will show EXACTLY what Lightsail resources are costing money

## 🎯 **Most Likely Causes (In Order)**

### 1. **Unattached Static IP** ($3.60/month) ← 90% likely
- **Symptom**: Exactly matches your $3.24 cost
- **Location**: Lightsail Console → Networking → Static IPs
- **Fix**: Delete unused static IP (FREE when attached, COSTLY when not)

### 2. **Old Snapshots** ($0.05/GB/month)  
- **Symptom**: Gradual cost increase over time
- **Location**: Lightsail Console → Snapshots
- **Fix**: Delete old instance/disk snapshots

### 3. **Different Region Resources**
- **Symptom**: Can't see resources in your current region
- **Location**: Check us-west-2, eu-west-1, etc.
- **Fix**: Switch regions and clean up

### 4. **Lightsail Containers/Databases**
- **Symptom**: Higher costs ($15+/month)
- **Location**: Lightsail Console → Containers/Databases
- **Fix**: Delete unused services

## ✅ **Quick Win Commands**

```bash
# Find static IPs in your default region (most likely cause)
aws lightsail get-static-ips --query 'staticIps[?!attachedTo].{Name:name,IP:ipAddress,CreatedAt:createdAt}' --output table

# Find snapshots consuming storage
aws lightsail get-instance-snapshots --query 'instanceSnapshots[].{Name:name,SizeGB:sizeInGb,CreatedAt:createdAt}' --output table

# Find databases
aws lightsail get-relational-databases --query 'relationalDatabases[].{Name:name,Engine:engine,InstanceClass:relationalDatabaseBlueprintId}' --output table
```

## 💰 **Expected Result**

You'll likely find:
- 1 unattached static IP address ($3.60/month) 
- OR 64GB worth of snapshots ($3.20/month)
- OR a combination of smaller resources

**Deleting these will save you $3.24/month = $38.88/year!**

## 🚨 **Immediate Action**

1. **Log into Lightsail Console now**: https://lightsail.aws.amazon.com/
2. **Click "Static IPs"** in the left menu
3. **Look for any unattached static IPs** 
4. **Delete them immediately** (they're costing you $3.60/month each)

This is probably a 2-minute fix that will save you $40/year!
