# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a clean, ultra-lightweight CTO Dashboard with ZERO architecture smell and ZERO code smell. Built for speed-to-market with <$0.05/month operating cost.

**Architecture Philosophy**: 
- **5-Year-Old Simple**: Frontend shows data, Backend gets data, Database stores data
- **Cost-Optimized**: Free tiers everywhere, SQLite file database
- **Clean Architecture**: Clear separation, no bloat, no gimmicks
- **Secure & Robust**: Simple = fewer attack vectors, easier to maintain

## Technology Stack

### Frontend (React)
- **React 18** with functional components only
- **TypeScript** for type safety
- **Vite** for blazing fast development
- **TailwindCSS** for styling (no custom CSS files)
- **Recharts** for data visualization
- **React Query** for API state management

### Backend (FastAPI)
- **FastAPI** with Python 3.11+ (fastest Python web framework)
- **SQLite** database (single file, no server needed)
- **SQLAlchemy** ORM (simple, clean database operations)
- **Pydantic** for data validation (built into FastAPI)
- **CORS** enabled for frontend communication

### Infrastructure (Free Tier)
- **Frontend**: Vercel (free tier, unlimited bandwidth)
- **Backend**: Railway.app (free tier, 512MB RAM, $0/month)
- **Database**: SQLite file (stored with backend, $0/month)
- **Domain**: Vercel subdomain (free)
- **SSL**: Automatic (free)

## Project Structure

```
ctodashboard/
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Assignment.tsx
│   │   │   └── MetricCard.tsx
│   │   ├── pages/          # Page components
│   │   │   ├── HomePage.tsx
│   │   │   └── AssignmentPage.tsx
│   │   ├── hooks/          # Custom hooks
│   │   │   └── useAssignments.ts
│   │   ├── types/          # TypeScript types
│   │   │   └── index.ts
│   │   ├── api/            # API client functions
│   │   │   └── client.ts
│   │   └── main.tsx        # App entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── backend/                # FastAPI Backend
│   ├── app/
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── database.py     # Database connection
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── crud.py         # Database operations
│   │   ├── routers/        # API routes
│   │   │   ├── assignments.py
│   │   │   └── metrics.py
│   │   └── main.py         # FastAPI app
│   ├── requirements.txt
│   └── database.db         # SQLite database file
└── README.md
```

## Clean Architecture Principles

### Database Schema (Simple SQLite Tables)

```sql
-- assignments table
CREATE TABLE assignments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    monthly_burn_rate INTEGER,
    team_size INTEGER
);

-- metrics table (time-series data)
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id TEXT,
    metric_type TEXT,  -- 'tech_stack', 'burn_rate', 'team_health'
    metric_name TEXT,
    value TEXT,        -- JSON blob for flexibility
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assignment_id) REFERENCES assignments (id)
);
```

### API Endpoints (RESTful & Simple)

```
GET  /assignments/              # List all assignments
POST /assignments/              # Create new assignment  
GET  /assignments/{id}          # Get assignment details
PUT  /assignments/{id}          # Update assignment
DELETE /assignments/{id}        # Archive assignment

GET  /assignments/{id}/metrics  # Get metrics for assignment
POST /assignments/{id}/metrics  # Add metric data
```

## Dashboard Metrics (Simple Categories)

### 1. Tech Stack Health
- Technologies used (React, Python, AWS, etc.)
- LLM API usage and costs
- Infrastructure spend tracking
- Security vulnerability count

### 2. Code Health  
- Test coverage percentage
- Code review completion rate
- Deployment success rate
- Bug count and resolution time

### 3. Business Health
- Feature delivery on-time percentage
- User satisfaction score (1-10)
- System uptime percentage
- Monthly revenue/cost ratio

### 4. Team Health
- Team size and roles
- Sprint velocity (story points)
- Employee satisfaction (1-10)
- Skills coverage matrix

## Development Commands

### Frontend Development (React)
```bash
cd frontend/
npm install              # Install dependencies
npm run dev             # Start development server (Vite)
npm run build           # Build for production
npm run preview         # Preview production build
```

### Backend Development (FastAPI)  
```bash
cd backend/
pip install -r requirements.txt    # Install dependencies
python -m uvicorn app.main:app --reload  # Start development server
```

### Database Management
```bash
cd backend/
python -c "from app.database import create_tables; create_tables()"  # Create tables
sqlite3 database.db ".schema"      # View database schema
sqlite3 database.db "SELECT * FROM assignments;"  # Query data
```

### Deployment Commands
```bash
# Frontend (Vercel)
cd frontend/ && vercel --prod

# Backend (Railway)
cd backend/ && railway login && railway deploy

# One-command deploy both
./deploy.sh
```

## Production Testing Strategy

### Frontend Testing (Jest + React Testing Library)
```bash
cd frontend/

# Unit tests - Components in isolation
npm run test:unit           # All component tests
npm run test:unit:watch     # Watch mode during development
npm run test:unit:coverage  # Coverage report (min 90%)

# Integration tests - API + Component interaction  
npm run test:integration    # API client + React Query tests

# Visual regression tests - Storybook + Chromatic
npm run test:visual         # Screenshot comparison tests
npm run storybook           # Component documentation
```

### Backend Testing (Pytest + FastAPI TestClient)
```bash
cd backend/

# Unit tests - Business logic only
python -m pytest tests/unit/ -v --cov=app --cov-report=html

# Integration tests - API + Database
python -m pytest tests/integration/ -v --cov=app

# Contract tests - API schema validation
python -m pytest tests/contract/ -v

# Performance tests - Load testing
python -m pytest tests/performance/ -v --benchmark-only
```

### End-to-End Testing (Playwright)
```bash
# E2E regression tests - Real browser automation
cd e2e/
npx playwright test                    # Full regression suite
npx playwright test --headed           # Watch tests run
npx playwright test --project=mobile   # Mobile-specific tests
npx playwright codegen                 # Record new tests
```

### Database Testing  
```bash
cd backend/
# Schema validation
python -m pytest tests/db/test_models.py -v

# Migration testing
python -c "from app.database import test_migrations; test_migrations()"

# Data integrity tests
python -m pytest tests/db/test_constraints.py -v
```

## Zero Code Smell Principles

### Frontend Rules
1. **One Component, One Purpose**: Each component does exactly one thing
2. **No Magic Numbers**: All values come from constants or props  
3. **TypeScript Strict Mode**: No `any` types allowed
4. **No Nested Ternary**: Use early returns or separate functions
5. **Props Interface Required**: All components have typed props

### Backend Rules  
1. **Single Responsibility**: Each function does one thing perfectly
2. **No Business Logic in Routes**: Routes only handle HTTP, delegate to services
3. **Type Everything**: Pydantic schemas for all data
4. **No Raw SQL**: Use SQLAlchemy ORM only
5. **Error Handling**: Every function handles its own errors

### Database Rules
1. **Normalized Schema**: No redundant data
2. **Foreign Keys**: Always use relationships
3. **Indexes**: Index all query columns
4. **Migrations**: Never edit schema directly

## Clean Code Modularity Rules

### File Size Limits (Enforced by Linting)
- **React Components**: Max 150 lines, single responsibility
- **API Routes**: Max 100 lines, delegate to services  
- **Database Models**: Max 50 lines per model
- **Utility Functions**: Max 30 lines, pure functions only
- **Test Files**: Max 200 lines, group related tests

### Module Structure (Maximum 7 Files Per Directory)
```
frontend/src/components/
├── MetricCard/
│   ├── MetricCard.tsx        # 50 lines max
│   ├── MetricCard.test.tsx   # 100 lines max  
│   ├── MetricCard.stories.tsx # 30 lines max
│   └── index.ts              # Export only
├── Dashboard/
│   ├── Dashboard.tsx         # 80 lines max
│   ├── Dashboard.hooks.ts    # 40 lines max
│   ├── Dashboard.test.tsx    # 120 lines max
│   └── index.ts
└── common/                   # Shared utilities
    ├── Button.tsx            # 30 lines max
    ├── Input.tsx             # 40 lines max
    └── index.ts
```

### Function Complexity (Max 5 Parameters, 3 Levels Deep)
```typescript
// ✅ Good - Single responsibility, clear parameters
function createMetricCard(
  title: string,
  value: number,
  trend: 'up' | 'down' | 'stable'
): MetricCardData {
  return {
    title,
    value: formatNumber(value),
    trend,
    timestamp: new Date().toISOString()
  }
}

// ❌ Bad - Too many parameters, complex logic  
function updateDashboardWithMetricsAndFiltersAndSorting(
  dashboard: Dashboard,
  metrics: Metric[],
  filters: Filter[],
  sortBy: string,
  sortOrder: string,
  pagination: Pagination,
  userPreferences: UserPrefs
) { /* 50+ lines of nested logic */ }
```

### Import Organization (Max 10 Imports Per File)
```typescript
// External libraries first (max 3)
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'

// Internal modules second (max 5)  
import { MetricCard } from '../MetricCard'
import { useAssignments } from '../hooks/useAssignments'
import { formatCurrency } from '../utils/formatters'

// Types last (max 2)
import type { Assignment, Metric } from '../types'
```

### Component Composition Over Inheritance
```typescript
// ✅ Good - Compose small, focused components
function AssignmentDashboard({ assignmentId }: Props) {
  const { data: assignment } = useAssignment(assignmentId)
  const { data: metrics } = useMetrics(assignmentId)
  
  if (!assignment) return <LoadingSpinner />
  
  return (
    <div>
      <AssignmentHeader assignment={assignment} />
      <MetricsGrid metrics={metrics} />
      <TechStackOverview techStack={assignment.techStack} />
    </div>
  )
}

// Each component is 20-50 lines, single purpose
function MetricsGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="grid grid-cols-4 gap-4">
      {metrics.map(metric => (
        <MetricCard key={metric.id} metric={metric} />
      ))}
    </div>
  )
}
```

### Backend Service Layer Pattern
```python
# routes/assignments.py (30 lines max - just HTTP handling)
@router.get("/assignments/{assignment_id}")
async def get_assignment(assignment_id: str, db: Session = Depends(get_db)):
    try:
        assignment = await AssignmentService.get_by_id(db, assignment_id)
        return AssignmentResponse.from_orm(assignment)
    except AssignmentNotFoundError as e:
        raise HTTPException(404, detail=str(e))

# services/assignment_service.py (80 lines max - business logic)
class AssignmentService:
    @staticmethod
    async def get_by_id(db: Session, assignment_id: str) -> Assignment:
        assignment = await AssignmentRepository.find_by_id(db, assignment_id)
        if not assignment:
            raise AssignmentNotFoundError(f"Assignment {assignment_id} not found")
        return assignment
    
    @staticmethod  
    async def create(db: Session, data: CreateAssignmentData) -> Assignment:
        # Single responsibility - just business logic
        validated_data = AssignmentValidator.validate_create(data)
        return await AssignmentRepository.create(db, validated_data)

# repositories/assignment_repository.py (60 lines max - data access)  
class AssignmentRepository:
    @staticmethod
    async def find_by_id(db: Session, assignment_id: str) -> Assignment | None:
        return db.query(Assignment).filter(Assignment.id == assignment_id).first()
    
    @staticmethod
    async def create(db: Session, data: dict) -> Assignment:
        assignment = Assignment(**data)
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment
```

### Utility Functions (Pure Functions Only)
```typescript
// utils/formatters.ts (max 150 lines total, 5 functions max)
export const formatCurrency = (amount: number, currency = 'USD'): string => 
  new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount)

export const formatDate = (date: string | Date): string => 
  format(typeof date === 'string' ? new Date(date) : date, 'MMM dd, yyyy')

export const formatPercentage = (value: number): string => 
  `${(value * 100).toFixed(1)}%`
```

## Production Security Hardening

### Authentication & Authorization
- **GitHub OAuth**: Enterprise-grade SSO, no password management
- **JWT tokens**: RS256 signing, 15-minute expiry, refresh token rotation
- **HTTPS Everywhere**: HSTS headers, no HTTP redirects allowed
- **RBAC**: Role-based access (admin, viewer) per assignment
- **Session Management**: Automatic logout, concurrent session limits

### API Security
- **Rate Limiting**: 100 req/min per IP, 1000 req/hour per user
- **Request Validation**: Pydantic strict validation, no raw data accepted
- **CORS**: Exact domain matching, no wildcards
- **CSP Headers**: Content Security Policy prevents XSS
- **API Versioning**: `/v1/` prefix for future compatibility

### Data Protection
- **Input Sanitization**: SQLAlchemy ORM prevents injection
- **Output Encoding**: All responses JSON-encoded
- **Secrets Management**: Environment variables, never in code/logs
- **Database Encryption**: SQLite with WAL mode, file permissions 600
- **Audit Logging**: All data changes logged with user attribution

## Cost Monitoring

### Monthly Cost Breakdown
```
Vercel Frontend:     $0.00 (free tier)
Railway Backend:     $0.00 (free tier, 512MB)  
Domain:             $0.00 (vercel subdomain)
Database:           $0.00 (SQLite file)
SSL Certificate:    $0.00 (automatic)
External APIs:      $0.00-0.05 (GitHub/Jira free tiers)
------------------------
Total Monthly Cost: $0.00-0.05
```

### Free Tier Limits
- **Vercel**: 100GB bandwidth, unlimited deploys
- **Railway**: 512MB RAM, 1GB storage, $0/month
- **GitHub API**: 5000 requests/hour (authenticated)
- **Jira API**: 10,000 requests/hour (free tier)

## CI/CD Pipeline (GitHub Actions)

### Pipeline Stages
```yaml
# .github/workflows/main.yml
name: Production CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # 1. Code Quality Gates
      - name: Lint & Format Check
        run: |
          cd frontend && npm run lint && npm run type-check
          cd backend && ruff check . && mypy .
      
      # 2. Security Scanning  
      - name: Security Audit
        run: |
          cd frontend && npm audit --audit-level=high
          cd backend && safety check && bandit -r app/
      
      # 3. Unit Tests (Parallel)
        run: |
          cd frontend && npm run test:unit:coverage
          cd backend && pytest tests/unit/ --cov=90
      
      # 4. Integration Tests
        run: |
          cd backend && pytest tests/integration/ -v
          cd frontend && npm run test:integration
      
      # 5. E2E Regression Tests
        run: |
          docker-compose up -d  # Start full stack
          cd e2e && npx playwright test
          docker-compose down

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      # 6. Deploy to Staging
      - name: Deploy Staging
        run: |
          vercel --prod --scope=staging
          railway deploy --environment=staging
      
      # 7. Smoke Tests on Staging
      - name: Production Smoke Tests
        run: |
          curl -f https://staging.ctodashboard.com/health
          cd e2e && npx playwright test smoke-tests.spec.ts
      
      # 8. Deploy to Production  
      - name: Deploy Production
        run: |
          vercel --prod 
          railway deploy --environment=production
```

### Quality Gates (Cannot Deploy Without)
- **Code Coverage**: Frontend 90%+, Backend 95%+
- **Security Scan**: Zero high/critical vulnerabilities  
- **Type Safety**: Zero TypeScript/mypy errors
- **E2E Tests**: 100% core user journeys passing
- **Performance**: Lighthouse score 95+
- **API Contract**: All endpoints match OpenAPI spec

### Automated Rollback
```bash
# If production health check fails after deploy
if ! curl -f https://ctodashboard.com/health; then
  echo "Health check failed - rolling back"
  vercel rollback
  railway rollback
  exit 1
fi
```

## Production Error Handling & Root Cause Analysis

### Frontend Error Boundary (React)
```typescript
// Every error includes full context for debugging
interface ErrorContext {
  errorId: string           // UUID for correlation  
  timestamp: string         // ISO timestamp
  userId: string           // Current user ID
  assignmentId?: string    // Current assignment context
  component: string        // Component where error occurred
  action: string          // User action that triggered error
  props: any              // Component props at time of error
  browserInfo: {
    userAgent: string
    url: string
    viewport: string
  }
  stackTrace: string      // Full stack trace
  networkStatus: boolean  // Online/offline status
}
```

### Backend Error Response (FastAPI)
```python
# Every API error provides actionable information
class APIError(Exception):
    def __init__(
        self, 
        message: str,
        error_code: str,
        user_message: str,      # What user should know
        root_cause: str,        # Technical root cause  
        suggested_action: str,  # What user can do
        context: Dict          # Request context
    ):
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.message = message
        self.error_code = error_code
        self.user_message = user_message
        self.root_cause = root_cause  
        self.suggested_action = suggested_action
        self.context = context

# Example error response:
{
  "error_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00.000Z", 
  "error_code": "ASSIGNMENT_NOT_FOUND",
  "user_message": "The assignment 'ideptech' could not be found",
  "root_cause": "Assignment ID 'ideptech' does not exist in database",
  "suggested_action": "Check the assignment ID or create a new assignment",
  "context": {
    "user_id": "user_123",
    "request_id": "req_456", 
    "assignment_id": "ideptech",
    "available_assignments": ["oldclient", "newproject"]
  }
}
```

### Database Error Handling
```python
# Every database operation has detailed error context
try:
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise APIError(
            message=f"Assignment {assignment_id} not found",
            error_code="ASSIGNMENT_NOT_FOUND",
            user_message=f"Assignment '{assignment_id}' could not be found",
            root_cause=f"No record with id='{assignment_id}' exists in assignments table",
            suggested_action="Check assignment ID spelling or create new assignment",
            context={
                "requested_id": assignment_id,
                "available_assignments": [a.id for a in db.query(Assignment).all()],
                "table": "assignments",
                "query": f"SELECT * FROM assignments WHERE id = '{assignment_id}'"
            }
        )
except SQLAlchemyError as e:
    raise APIError(
        message="Database operation failed",
        error_code="DATABASE_ERROR", 
        user_message="A database error occurred. Please try again",
        root_cause=f"SQLAlchemy error: {str(e)}",
        suggested_action="Retry the operation or contact support if persists",
        context={
            "operation": "SELECT",
            "table": "assignments", 
            "sql_error": str(e),
            "db_file": "database.db"
        }
    )
```

## Production Monitoring & Observability

### Health Checks & Uptime Monitoring
```python
# backend/app/health.py - Simple health endpoint
from fastapi import APIRouter
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check():
    # Database connectivity
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Disk space (SQLite file size)
    import os
    db_size = os.path.getsize("database.db") if os.path.exists("database.db") else 0
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_status,
            "disk_usage": f"{db_size / 1024 / 1024:.2f}MB"
        }
    }
```

### Structured Logging (JSON Format)
```python
# backend/app/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra context if available
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'assignment_id'):
            log_entry["assignment_id"] = record.assignment_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
            
        return json.dumps(log_entry)

# Usage in routes
logger = logging.getLogger(__name__)

@router.get("/assignments/{assignment_id}")
async def get_assignment(assignment_id: str):
    logger.info(
        "Assignment request started",
        extra={
            "user_id": "current_user_id",
            "assignment_id": assignment_id,
            "request_id": "unique_request_id"
        }
    )
```

### Frontend Error Tracking & Analytics
```typescript
// frontend/src/utils/monitoring.ts
interface ErrorReport {
  errorId: string
  timestamp: string
  userId: string
  assignmentId?: string
  errorType: 'api_error' | 'component_error' | 'network_error'
  message: string
  stackTrace: string
  userAgent: string
  url: string
  component: string
}

class MonitoringService {
  static reportError(error: Error, context: Partial<ErrorReport>) {
    const report: ErrorReport = {
      errorId: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      userId: getCurrentUserId(),
      errorType: context.errorType || 'component_error',
      message: error.message,
      stackTrace: error.stack || '',
      userAgent: navigator.userAgent,
      url: window.location.href,
      component: context.component || 'unknown',
      ...context
    }
    
    // Send to logging endpoint (async, don't block UI)
    fetch('/api/v1/logs/frontend-error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(report)
    }).catch(() => {
      // Store locally if network fails, retry later
      localStorage.setItem(`error_${report.errorId}`, JSON.stringify(report))
    })
  }
}

// Usage in React Error Boundary
function ErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ReactErrorBoundary
      onError={(error, errorInfo) => {
        MonitoringService.reportError(error, {
          errorType: 'component_error',
          component: errorInfo.componentStack.split('\n')[1]?.trim() || 'unknown'
        })
      }}
      fallback={<ErrorFallback />}
    >
      {children}
    </ReactErrorBoundary>
  )
}
```

### Performance Monitoring (Web Vitals)
```typescript
// frontend/src/utils/performance.ts
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals'

function sendToAnalytics(metric: any) {
  fetch('/api/v1/analytics/performance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      timestamp: new Date().toISOString(),
      userId: getCurrentUserId(),
      url: window.location.href,
      ...metric
    })
  }).catch(() => {
    // Ignore analytics failures
  })
}

// Measure Core Web Vitals
getCLS(sendToAnalytics)  // Cumulative Layout Shift
getFID(sendToAnalytics)  // First Input Delay  
getFCP(sendToAnalytics)  // First Contentful Paint
getLCP(sendToAnalytics)  // Largest Contentful Paint
getTTFB(sendToAnalytics) // Time to First Byte
```

### Alert System (Simple Email Notifications)
```python
# backend/app/alerts.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertService:
    @staticmethod
    async def send_alert(
        alert_type: str,
        message: str,
        severity: str = "warning",  # info, warning, critical
        context: dict = None
    ):
        if severity == "critical":
            # Send immediately
            await AlertService._send_email(
                subject=f"🚨 CTO Dashboard Alert: {alert_type}",
                body=f"""
                Alert Type: {alert_type}
                Severity: {severity}
                Message: {message}
                Timestamp: {datetime.utcnow().isoformat()}
                Context: {json.dumps(context, indent=2)}
                
                View Dashboard: https://ctodashboard.com
                """
            )
        
    @staticmethod
    async def _send_email(subject: str, body: str):
        # Use environment variables for email config
        sender_email = os.getenv("ALERT_EMAIL_FROM")
        sender_password = os.getenv("ALERT_EMAIL_PASSWORD")  
        recipient_email = os.getenv("ALERT_EMAIL_TO")
        
        if not all([sender_email, sender_password, recipient_email]):
            logger.warning("Email alerts not configured")
            return
            
        # Simple SMTP email sending
        # Implementation details...

# Usage - automatic alerts for critical errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    await AlertService.send_alert(
        alert_type="Unhandled Exception",
        message=str(exc),
        severity="critical",
        context={
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers),
            "stack_trace": traceback.format_exc()
        }
    )
```

### Cost Monitoring & Budget Alerts
```python
# backend/app/cost_monitor.py
class CostMonitor:
    @staticmethod
    async def check_monthly_costs():
        """Run daily to monitor costs across all services"""
        costs = {
            "vercel_bandwidth": await CostMonitor._check_vercel_usage(),
            "railway_usage": await CostMonitor._check_railway_usage(),
            "external_apis": await CostMonitor._check_api_usage()
        }
        
        total_monthly_cost = sum(costs.values())
        
        if total_monthly_cost > 0.03:  # 60% of $0.05 budget
            await AlertService.send_alert(
                alert_type="Budget Alert",
                message=f"Monthly costs at ${total_monthly_cost:.4f} (60% of budget)",
                severity="warning",
                context={"cost_breakdown": costs}
            )
            
        if total_monthly_cost > 0.05:  # Over budget
            await AlertService.send_alert(
                alert_type="Budget Exceeded",
                message=f"Monthly costs ${total_monthly_cost:.4f} exceed $0.05 budget",
                severity="critical",
                context={"cost_breakdown": costs}
            )
```