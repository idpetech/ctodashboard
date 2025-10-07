#!/bin/bash
# Pre-deployment validation script
# Run this before every git push to catch errors early

set -e  # Exit on first error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           PRE-DEPLOYMENT VALIDATION PIPELINE              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# 1. Syntax Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  SYNTAX CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FILES=(
    "integrated_dashboard.py"
    "routes/api_routes.py"
    "services/service_manager.py"
    "services/embedded/aws_metrics.py"
    "services/embedded/github_metrics.py"
    "services/embedded/jira_metrics.py"
    "services/embedded/openai_metrics.py"
)

for file in "${FILES[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "  ✅ $file"
    else
        echo -e "  ${RED}❌ $file - SYNTAX ERROR${NC}"
        python3 -m py_compile "$file"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# 2. Check for incomplete decorators
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  CHECKING FOR INCOMPLETE DECORATORS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if grep -n "@app.route" services/embedded/*.py services/service_manager.py 2>/dev/null; then
    echo -e "  ${RED}❌ FOUND @app.route IN SERVICE FILES (should only be in routes/api_routes.py)${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo "  ✅ No route decorators in service files"
fi
echo ""

# 3. Check for missing imports
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  CHECKING FOR MISSING IMPORTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check each service file has required imports
check_imports() {
    local file=$1
    local required_imports=("${@:2}")
    local missing=0
    
    for import in "${required_imports[@]}"; do
        if ! grep -q "^import $import\|^from $import" "$file"; then
            echo -e "  ${RED}❌ $file missing: import $import${NC}"
            missing=$((missing + 1))
            ERRORS=$((ERRORS + 1))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        echo "  ✅ $file has all required imports"
    fi
}

check_imports "services/embedded/aws_metrics.py" "os" "boto3"
check_imports "services/embedded/github_metrics.py" "os" "requests"
check_imports "services/embedded/jira_metrics.py" "os" "requests"
check_imports "services/embedded/openai_metrics.py" "os" "requests"
check_imports "services/service_manager.py" "os"
check_imports "routes/api_routes.py" "os" "json"
echo ""

# 4. Check for missing __init__.py files
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  CHECKING FOR MISSING __init__.py FILES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
REQUIRED_INIT_FILES=(
    "services/__init__.py"
    "services/embedded/__init__.py"
    "routes/__init__.py"
)

for init_file in "${REQUIRED_INIT_FILES[@]}"; do
    if [ -f "$init_file" ]; then
        echo "  ✅ $init_file exists"
    else
        echo -e "  ${RED}❌ $init_file MISSING${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# 5. Check for FEATURE_FLAGS definition
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  CHECKING FOR FEATURE_FLAGS DEFINITION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if grep -q "^FEATURE_FLAGS = {" services/service_manager.py; then
    echo "  ✅ FEATURE_FLAGS defined in service_manager.py"
else
    echo -e "  ${RED}❌ FEATURE_FLAGS not defined in service_manager.py${NC}"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "^FEATURE_FLAGS = {" integrated_dashboard.py; then
    echo "  ✅ FEATURE_FLAGS defined in integrated_dashboard.py"
else
    echo -e "  ${RED}❌ FEATURE_FLAGS not defined in integrated_dashboard.py${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 6. Static analysis
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  STATIC ANALYSIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if python3 static_check.py; then
    echo ""
else
    ERRORS=$((ERRORS + 1))
fi

# 7. Check requirements.txt
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  CHECKING REQUIREMENTS.TXT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
REQUIRED_PACKAGES=("gunicorn" "Flask" "boto3" "requests")
for package in "${REQUIRED_PACKAGES[@]}"; do
    if grep -qi "^$package" requirements.txt; then
        echo "  ✅ $package in requirements.txt"
    else
        echo -e "  ${RED}❌ $package MISSING from requirements.txt${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Final summary
echo "╔════════════════════════════════════════════════════════════╗"
if [ $ERRORS -eq 0 ]; then
    echo -e "║  ${GREEN}✅ ALL CHECKS PASSED - SAFE TO DEPLOY${NC}                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    exit 0
else
    echo -e "║  ${RED}❌ $ERRORS ERROR(S) FOUND - DO NOT DEPLOY${NC}                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${RED}Fix the errors above before deploying to Railway${NC}"
    exit 1
fi
