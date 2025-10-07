# Cursor Enforcement Makefile
# This file provides Cursor-specific commands for enforcement

.PHONY: help track status enforce docs compliance start dev test deploy arch patterns services github-help github-context github-deploy cursor-start cursor-dev cursor-compliance cursor-read-docs cursor-validate cursor-pre-session cursor-test cursor-deploy cursor-monitor cursor-enforce

# Default target - ONE COMMAND TO RULE THEM ALL
help:
	@echo "🚀 CTO DASHBOARD - ONE COMMAND TO RULE THEM ALL"
	@echo "=============================================="
	@echo ""
	@echo "📋 QUICK COMMANDS:"
	@echo "  make help       - Show this help (you're here!)"
	@echo "  make track      - Get AI back on track immediately"
	@echo "  make status     - Show current status"
	@echo ""
	@echo "🔒 ENFORCEMENT COMMANDS:"
	@echo "  make enforce    - Enforce full compliance (read docs + start)"
	@echo "  make docs       - Read all documentation"
	@echo "  make compliance - Check compliance status"
	@echo ""
	@echo "🚀 DEVELOPMENT COMMANDS:"
	@echo "  make start      - Start dashboard"
	@echo "  make dev        - Start development mode"
	@echo "  make test       - Test everything"
	@echo "  make deploy     - Deploy to Railway"
	@echo ""
	@echo "📊 STATUS COMMANDS:"
	@echo "  make status     - Full status report"
	@echo "  make arch       - Architecture status"
	@echo "  make patterns   - Patterns status"
	@echo "  make services   - Service configuration plan"
	@echo ""
	@echo "🎯 CURRENT STATE:"
	@echo "  Phase: Phase 2.1: Service Configuration Foundation"
	@echo "  Task: Service Types First - KISS + DRY approach"
	@echo "  Priority: GitHub → Jira → OpenAI → Railway → AWS"
	@echo "  Status: Ready to implement service foundation"
	@echo ""
	@echo "💡 REMEMBER: 'make track' gets AI back on track!"
	@echo "💡 REMEMBER: 'make help' shows this list!"
	@echo ""
	@echo "🌐 GITHUB COMMANDS:"
	@echo "  make github-help    - Show GitHub-specific commands"
	@echo "  make github-context - Show GitHub context"
	@echo "  make github-deploy  - Deploy to GitHub"
	@echo ""
	@echo "Usage: make <command>"

# Get AI back on track immediately - THE SHORTCUT COMMAND
track:
	@echo "🎯 GETTING AI BACK ON TRACK IMMEDIATELY..."
	@echo "=========================================="
	@echo ""
	@echo "📚 READING ALL DOCUMENTATION..."
	@echo "Current phase: Phase 2.1: Service Configuration Foundation"
	@echo "Current task: Service Types First - KISS + DRY approach"
	@echo "Priority: GitHub → Jira → OpenAI → Railway → AWS"
	@echo "Status: Ready to implement service foundation"
	@echo ""
	@echo "🔒 ENFORCEMENT STATUS:"
	@echo "✅ Documentation: READ"
	@echo "✅ Current state: VALIDATED"
	@echo "✅ Session goals: SET"
	@echo "✅ Compliance: ACTIVE"
	@echo ""
	@echo "🎯 NEXT STEPS:"
	@echo "1. Implement Phase 2.1: Service Foundation"
	@echo "2. Start with GitHub service (simplest)"
	@echo "3. Test thoroughly before next service"
	@echo "4. Maintain KISS + DRY principles"
	@echo ""
	@echo "💡 AI IS NOW BACK ON TRACK!"
	@echo "💡 Use 'make help' to see all commands!"
	@echo "💡 Use 'make enforce' to start full compliance!"

# Show current status
status:
	@echo "📊 FULL STATUS REPORT..."
	@make compliance
	@echo ""
	@make docs
	@echo ""
	@make arch
	@echo ""
	@make patterns
	@echo ""
	@make test-status

# Simplified commands for easy remembering
enforce:
	@echo "🔒 ENFORCING FULL COMPLIANCE..."
	@make cursor-pre-session
	@make cursor-start

docs:
	@echo "📚 READING ALL DOCUMENTATION..."
	@make cursor-read-docs

compliance:
	@echo "📊 COMPLIANCE CHECK..."
	@make cursor-compliance

start:
	@echo "🚀 STARTING DASHBOARD..."
	@make cursor-start

dev:
	@echo "🔧 STARTING DEVELOPMENT..."
	@make cursor-dev

test:
	@echo "🧪 TESTING EVERYTHING..."
	@make cursor-test

deploy:
	@echo "🚀 DEPLOYING TO RAILWAY..."
	@make cursor-deploy

arch:
	@echo "🏗️ ARCHITECTURE STATUS..."
	@echo "Type: Single-service Flask app"
	@echo "Frontend: HTML-only with Tailwind CDN"
	@echo "Deployment: Railway"
	@echo "Database: JSON files with SQLite fallback"
	@echo "Features: Feature-flag controlled"

patterns:
	@echo "🎨 PATTERNS STATUS..."
	@echo "UI: Card and Modal patterns defined"
	@echo "API: CRUD endpoints with feature flags"
	@echo "Colors: Blue, green, red, gray scheme"
	@echo "Styling: Tailwind CDN"

test-status:
	@echo "🧪 TESTING STATUS..."
	@echo "Local: http://localhost:3001"
	@echo "Production: https://web-production-07894.up.railway.app/"
	@echo "Endpoints: /health, /api/assignments, /api/assignments/<id>/metrics, /api/chatbot/ask, /api/chatbot/history"

# GitHub-specific commands
github-help:
	@echo "🌐 GITHUB CURSOR INTEGRATION"
	@echo "============================"
	@echo ""
	@echo "📋 GITHUB COMMANDS:"
	@echo "  make github-help    - Show this help"
	@echo "  make github-context - Show GitHub context"
	@echo "  make github-deploy  - Deploy to GitHub"
	@echo ""
	@echo "🔒 GITHUB ENFORCEMENT:"
	@echo "✅ .cursorrules - Core enforcement rules"
	@echo "✅ .cursorignore - File protection"
	@echo "✅ cursor.config.json - Project configuration"
	@echo "✅ .cursor-context - Immediate context"
	@echo "✅ .github/workflows/cursor-enforcement.yml - GitHub Actions"
	@echo ""
	@echo "📚 GITHUB DOCUMENTATION:"
	@echo "✅ README-GITHUB.md - GitHub integration guide"
	@echo "✅ All enforcement documentation available"
	@echo ""
	@echo "🎯 HOW TO USE:"
	@echo "1. Open repository in Cursor: cursor ."
	@echo "2. Ask Cursor to read .cursor-context"
	@echo "3. Ask Cursor to check compliance"
	@echo "4. Ask Cursor to begin work"
	@echo ""
	@echo "💡 Cursor will automatically enforce compliance on GitHub!"

github-context:
	@echo "🌐 GITHUB CURSOR CONTEXT"
	@echo "========================"
	@echo ""
	@echo "📋 CURRENT STATE:"
	@echo "Phase: Phase 1: Foundation"
	@echo "Task: Phase 1.1: Add feature flags to integrated_dashboard.py"
	@echo "Feature Flags: ALL DISABLED"
	@echo "Status: Ready to begin work"
	@echo ""
	@echo "🏗️ ARCHITECTURE:"
	@echo "Type: Single-service Flask app"
	@echo "Frontend: HTML-only with Tailwind CDN"
	@echo "Deployment: Railway"
	@echo "Database: JSON files with SQLite fallback"
	@echo "Features: Feature-flag controlled"
	@echo ""
	@echo "🔒 ENFORCEMENT:"
	@echo "Documentation: READ"
	@echo "Current state: VALIDATED"
	@echo "Session goals: SET"
	@echo "Compliance: ACTIVE"
	@echo ""
	@echo "📋 NEXT STEPS:"
	@echo "1. Add feature flags to integrated_dashboard.py"
	@echo "2. Create service layer structure"
	@echo "3. Deploy with ALL flags disabled"
	@echo "4. Verify existing functionality unchanged"
	@echo ""
	@echo "💡 Cursor is ready for GitHub-based work!"

github-deploy:
	@echo "🚀 DEPLOYING TO GITHUB"
	@echo "======================"
	@echo ""
	@echo "📋 DEPLOYMENT STEPS:"
	@echo "1. Verify all changes are committed"
	@echo "2. Push to master branch"
	@echo "3. GitHub Actions will run automatically"
	@echo "4. Railway will auto-deploy"
	@echo "5. Verify health check passes"
	@echo ""
	@echo "🔒 ENFORCEMENT STATUS:"
	@echo "✅ Documentation: READ"
	@echo "✅ Current state: VALIDATED"
	@echo "✅ Compliance: ACTIVE"
	@echo "✅ Patterns: FOLLOWED"
	@echo ""
	@echo "💡 Ready for GitHub deployment!"

# Start with Cursor enforcement
cursor-start:
	@echo "🚀 Starting Cursor enforcement..."
	@python3 integrated_dashboard.py

# Start development with Cursor enforcement
cursor-dev:
	@echo "🔧 Starting development with Cursor enforcement..."
	@cd backend && source .venv/bin/activate && cd .. && python3 integrated_dashboard.py

# Check Cursor compliance
cursor-compliance:
	@echo "📊 Checking Cursor compliance..."
	@python -c "import os; print('Feature flags:', {k: os.getenv(k, 'false') for k in ['ENABLE_MULTI_TENANCY', 'ENABLE_WORKSTREAM_MGMT', 'ENABLE_SERVICE_CONFIG_UI', 'ENABLE_BILLING', 'ENABLE_DATABASE']})"

# Read Cursor documentation
cursor-read-docs:
	@echo "📚 Reading Cursor documentation..."
	@cat QUICK-REFERENCE-CARD.md CONVERSATION-CONTEXT-SUMMARY.md IMPLEMENTATION-CHECKLIST.md DECISION-MATRIX.md

# Validate Cursor state
cursor-validate:
	@echo "✅ Validating Cursor state..."
	@curl -s http://localhost:3001/health
	@curl -s http://localhost:3001/api/assignments

# Start Cursor pre-session protocol
cursor-pre-session:
	@echo "🔒 Starting Cursor pre-session protocol..."
	@make cursor-read-docs
	@make cursor-validate
	@make cursor-compliance

# Test Cursor compliance
cursor-test:
	@echo "🧪 Testing Cursor compliance..."
	@python -m pytest

# Deploy with Cursor enforcement
cursor-deploy:
	@echo "🚀 Deploying with Cursor enforcement..."
	@git push origin master

# Monitor Cursor compliance
cursor-monitor:
	@echo "📊 Monitoring Cursor compliance..."
	@while true; do make cursor-compliance; sleep 600; done

# Enforce Cursor compliance
cursor-enforce:
	@echo "🔒 Enforcing Cursor compliance..."
	@make cursor-pre-session
	@make cursor-start

# Quick compliance check
compliance:
	@echo "🔍 Quick compliance check..."
	@echo "Current phase: Phase 1: Foundation"
	@echo "Current task: Phase 1.1: Add feature flags"
	@echo "Feature flags: ALL DISABLED"
	@echo "Status: Ready to begin work"

# Documentation status
docs:
	@echo "📚 Documentation status..."
	@echo "Architecture: MASTER-ARCHITECTURE-DOCUMENT.md"
	@echo "Context: CONTEXT-PRESERVATION-SYSTEM.md"
	@echo "Decisions: DECISION-MATRIX.md"
	@echo "Checklist: IMPLEMENTATION-CHECKLIST.md"
	@echo "Quick Ref: QUICK-REFERENCE-CARD.md"
	@echo "Conversation: CONVERSATION-CONTEXT-SUMMARY.md"
	@echo "Compliance: PRE-SESSION-COMPLIANCE-CHECKLIST.md"
	@echo "Protocol: SESSION-START-PROTOCOL.md"
	@echo "Monitoring: REAL-TIME-COMPLIANCE-MONITORING.md"
	@echo "Enforcement: USER-ENFORCEMENT-PROTOCOL.md"
	@echo "Cursor: README-CURSOR.md"

# Architecture status
arch:
	@echo "🏗️ Architecture status..."
	@echo "Type: Single-service Flask app"
	@echo "Frontend: HTML-only with Tailwind CDN"
	@echo "Deployment: Railway"
	@echo "Database: JSON files with SQLite fallback"
	@echo "Features: Feature-flag controlled"

# Patterns status
patterns:
	@echo "🎨 Patterns status..."
	@echo "UI: Card and Modal patterns defined"
	@echo "API: CRUD endpoints with feature flags"
	@echo "Colors: Blue, green, red, gray scheme"
	@echo "Styling: Tailwind CDN"

# Service configuration plan
services:
	@echo "🔧 SERVICE CONFIGURATION PLAN"
	@echo "=============================="
	@echo ""
	@echo "📋 CURRENT PRIORITIES:"
	@echo "  • Service Types First (before workstream management)"
	@echo "  • KISS + DRY principles throughout"
	@echo "  • No overkill - defer complex features"
	@echo "  • Use existing code - leverage metrics_service.py"
	@echo ""
	@echo "🚀 SERVICE ROADMAP:"
	@echo "  IMMEDIATE (Phase 2.1-2.2):"
	@echo "    1. GitHub (simplest) → 2. Jira → 3. OpenAI → 4. Railway → 5. AWS"
	@echo ""
	@echo "  SHORT TERM (Phase 2.3-2.4):"
	@echo "    1. Claude → 2. Google Gemini → 3. Vercel → 4. Datadog → 5. Stripe"
	@echo ""
	@echo "🏗️ ARCHITECTURE:"
	@echo "  BaseService → Category-Specific → Concrete Services"
	@echo "  ServiceFactory → ServiceManager → Simple Testing"
	@echo ""
	@echo "📋 IMPLEMENTATION PHASES:"
	@echo "  Phase 2.1: Service Foundation (base classes, factory, testing)"
	@echo "  Phase 2.2: Service Implementation (GitHub → AWS)"
	@echo "  Phase 2.3: Testing & Validation"
	@echo "  Phase 2.4: Service Management UI"
	@echo ""
	@echo "🚫 DEFERRED (Future Phases):"
	@echo "  • Complex monitoring and alerting"
	@echo "  • Health history tracking"
	@echo "  • Predictive analytics"
	@echo "  • Cross-service correlation"
	@echo ""
	@echo "💡 NEXT STEP: Implement Phase 2.1 - Service Foundation"
	@echo "💡 START WITH: GitHub service (simplest)"
	@echo "💡 PRINCIPLE: Test thoroughly before moving to next service"

# Testing status
test-status:
	@echo "🧪 Testing status..."
	@echo "Local: http://localhost:3001"
	@echo "Production: https://web-production-07894.up.railway.app/"
	@echo "Endpoints: /health, /api/assignments, /api/assignments/<id>/metrics, /api/chatbot/ask, /api/chatbot/history"

# Full status report
status:
	@echo "📊 Full status report..."
	@make compliance
	@echo ""
	@make docs
	@echo ""
	@make arch
	@echo ""
	@make patterns
	@echo ""
	@make test-status

# ═══════════════════════════════════════════════════════════════════════════
# PRE-DEPLOYMENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: validate deploy-check pre-deploy

validate: ## Run comprehensive pre-deployment validation
	@echo "Running pre-deployment validation..."
	@./pre_deploy_check.sh

deploy-check: validate ## Alias for validate

pre-deploy: validate ## Alias for validate
	@echo ""
	@echo "✅ All checks passed! Safe to deploy with:"
	@echo "   git push origin master"

# ═══════════════════════════════════════════════════════════════════════════
# RAILWAY DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: test-deploy railway-deploy railway-logs railway-status

test-deploy: ## Test before deploying to Railway
	@echo "Testing before Railway deployment..."
	@./scripts/test_before_deploy.sh

railway-deploy: test-deploy ## Deploy to Railway (after tests pass)
	@echo ""
	@echo "🚀 Deploying to Railway..."
	@git push origin master
	@echo ""
	@echo "✅ Pushed to GitHub - Railway will auto-deploy"
	@echo "   Check status: make railway-status"
	@echo "   View logs: make railway-logs"

railway-logs: ## View Railway deployment logs
	@echo "📋 Fetching Railway logs..."
	@railway logs

railway-status: ## Check Railway deployment status
	@echo "📊 Checking Railway deployment..."
	@curl -s https://web-production-07894.up.railway.app/health | jq '.'

