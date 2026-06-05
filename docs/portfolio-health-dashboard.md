# Portfolio Health Dashboard for Fractional CTOs

**Document Version:** 1.0  
**Date:** 2026-06-05  
**Target:** Transform Overview tab into actionable CTO decision support interface  

---

## Executive Summary

Transform the current basic Overview page into a **Portfolio Health Dashboard** that answers the critical questions a Fractional CTO needs answered within 30 seconds:

1. **What requires my immediate attention?**
2. **Which assignments are healthy vs. at risk?**
3. **Which connectors are failing and blocking insights?**
4. **What is my total portfolio burn rate and trajectory?**
5. **What changed since my last check?**

The dashboard shifts from passive metrics display to active operational intelligence.

---

## Current State Analysis

### Existing Overview Functionality
- Basic assignment status counts (Active, Completed, Archived)
- Total team size aggregation
- Monthly burn rate summation
- Simple assignment list table
- Service enablement indicators

### Current Data Sources
- **Core Tables:** `assignments`, `workspaces`, `credentials`, `audit_logs`
- **Metrics:** GitHub, Jira, AWS, OpenAI, Railway connectors
- **Status:** Basic assignment status tracking
- **Financials:** Monthly burn rate per assignment

### Gaps for CTO Decision Making
- No attention prioritization system
- No health scoring or risk assessment
- No change detection or trending
- No connector health monitoring
- No actionable alerts or recommendations
- No portfolio-level insights beyond simple aggregation

---

## 30-Second CTO Decision Framework

A Fractional CTO scanning the dashboard needs to quickly assess:

### Attention Hierarchy (Top to Bottom)
1. **CRITICAL ALERTS** — Immediate action required
2. **PORTFOLIO HEALTH** — Overall status at-a-glance
3. **CONNECTOR STATUS** — Data pipeline health
4. **BURN TRAJECTORY** — Financial trend analysis
5. **RECENT CHANGES** — What's different since last check

### Decision Context Requirements
- **Time-sensitive issues** highlighted prominently
- **Risk indicators** visible without drilling down
- **Financial variance** from expected burn rates
- **Data quality** assessment for informed decisions
- **Trend direction** for each key metric

---

## UX Layout Design

### Header Section (Always Visible)
```
┌─ CRITICAL ALERTS ────────────────────────────────────────────────────┐
│ 🚨 3 assignments over budget | 🔴 AWS connector down 2h | ⚠️ 5 failed deployments │
└──────────────────────────────────────────────────────────────────────┘
```

### Main Dashboard Grid (2-Column Layout)

#### Left Column: Portfolio Health
```
┌─ PORTFOLIO HEALTH SCORE ─────┐  ┌─ BURN TRAJECTORY ─────────────────┐
│ 🟢 84/100 HEALTHY            │  │ 📈 Monthly: $47K (+$3K from last) │
│ ↗️ +5 points this week       │  │ 📊 Trend: +6.8% growth rate      │
│                              │  │ 🎯 Target: $50K max              │
│ 🟢 6 Healthy                 │  │ ⏰ Runway: 14 months @ current   │
│ 🟡 2 At Risk                 │  │                                   │
│ 🔴 1 Critical                │  └───────────────────────────────────┘
└──────────────────────────────┘
```

#### Right Column: Operational Intelligence
```
┌─ CONNECTOR HEALTH ───────────┐  ┌─ RECENT CHANGES ──────────────────┐
│ 🟢 GitHub: ✓ 2min ago       │  │ 🕒 Last 24h                       │
│ 🟡 Jira: ⚠️ 15min delay     │  │                                   │
│ 🔴 AWS: ❌ Down 2h          │  │ • ProjectX budget +20%            │
│ 🟢 Railway: ✓ 5min ago      │  │ • ClientY team +2 people          │
│                              │  │ • AWS costs ↗️ spike detected     │
│ Last sync: 3min ago          │  │ • 3 deployments failed           │
│ Auto-refresh: ON             │  │                                   │
└──────────────────────────────┘  └───────────────────────────────────┘
```

### Assignment Health Matrix (Bottom Section)
```
┌─ ASSIGNMENT HEALTH MATRIX ──────────────────────────────────────────────────────┐
│                                                                                  │
│ 🟢 ProjectAlpha    ✓ On track    $8K/mo (-$500)    👥6    ↗️ Strong metrics     │
│ 🟢 ClientBravo     ✓ Healthy     $12K/mo (stable)  👥4    → Steady progress    │
│ 🟡 ProductGamma    ⚠️ At risk    $15K/mo (+$2K)    👥8    ↘️ Deploy issues     │
│ 🔴 ProjectDelta    🚨 Critical   $18K/mo (+$5K)    👥12   ⬇️ Multiple alerts   │
│                                                                                  │
│ [View Details] [Export Report] [Schedule Review]                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Mobile-First Responsive Adjustments
- **Phone:** Stack cards vertically, critical alerts stay pinned
- **Tablet:** 2x2 grid for main cards, simplified assignment list
- **Desktop:** Full layout as described above

---

## Data Model Extensions

### New Tables Required

#### `portfolio_health_snapshots`
```sql
CREATE TABLE portfolio_health_snapshots (
    id SERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    overall_score INTEGER NOT NULL,           -- 0-100 health score
    financial_health INTEGER NOT NULL,        -- Sub-score for burn rate health
    operational_health INTEGER NOT NULL,      -- Sub-score for connector/deployment health
    team_health INTEGER NOT NULL,            -- Sub-score for team metrics
    total_monthly_burn INTEGER NOT NULL,      -- Snapshot of total portfolio burn
    assignments_healthy INTEGER NOT NULL,     -- Count of healthy assignments
    assignments_at_risk INTEGER NOT NULL,     -- Count of at-risk assignments
    assignments_critical INTEGER NOT NULL,    -- Count of critical assignments
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX(workspace_id, snapshot_date)
);
```

#### `assignment_health_scores`
```sql
CREATE TABLE assignment_health_scores (
    id SERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    health_score INTEGER NOT NULL,            -- 0-100 overall health
    attention_level TEXT NOT NULL,            -- 'healthy', 'at_risk', 'critical'
    financial_score INTEGER,                  -- Budget vs actual performance
    operational_score INTEGER,               -- Deployment success, uptime
    team_score INTEGER,                       -- Velocity, satisfaction
    risk_factors TEXT,                        -- JSON array of identified risks
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(workspace_id, assignment_id),
    INDEX(workspace_id, attention_level, health_score)
);
```

#### `connector_health_status`
```sql
CREATE TABLE connector_health_status (
    id SERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    connector_type TEXT NOT NULL,             -- 'github', 'jira', 'aws', 'openai'
    status TEXT NOT NULL,                     -- 'healthy', 'degraded', 'down'
    last_success TIMESTAMP,                   -- Last successful data fetch
    last_failure TIMESTAMP,                   -- Last failed attempt
    failure_count INTEGER DEFAULT 0,          -- Consecutive failures
    error_message TEXT,                       -- Last error details
    response_time_ms INTEGER,                 -- Last successful response time
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(workspace_id, assignment_id, connector_type),
    INDEX(workspace_id, status, last_success)
);
```

#### `portfolio_change_events`
```sql
CREATE TABLE portfolio_change_events (
    id SERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    event_type TEXT NOT NULL,                 -- 'budget_change', 'team_change', 'status_change', 'deployment'
    entity_type TEXT NOT NULL,                -- 'assignment', 'connector', 'portfolio'
    entity_id TEXT NOT NULL,                  -- assignment_id or other identifier
    change_description TEXT NOT NULL,         -- Human-readable change summary
    previous_value TEXT,                      -- JSON of old state
    new_value TEXT,                          -- JSON of new state
    impact_level TEXT DEFAULT 'low',         -- 'low', 'medium', 'high'
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX(workspace_id, detected_at DESC, impact_level)
);
```

### Extended Assignment Schema
Add fields to existing `assignments` table:
```sql
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS 
    health_score INTEGER DEFAULT 75,
    attention_level TEXT DEFAULT 'healthy',
    last_health_check TIMESTAMP,
    target_monthly_burn INTEGER,              -- Budget target for variance calculation
    deployment_success_rate DECIMAL(5,2),    -- Last 30 days deployment success %
    last_deployment_at TIMESTAMP;
```

---

## Backend API Requirements

### New API Endpoints

#### Portfolio Health API
```python
# GET /api/v1/portfolio/health
{
    "overall_score": 84,
    "trend": "+5",
    "breakdown": {
        "financial_health": 78,
        "operational_health": 89,
        "team_health": 85
    },
    "assignment_counts": {
        "healthy": 6,
        "at_risk": 2, 
        "critical": 1
    },
    "total_monthly_burn": 47000,
    "burn_variance": 3000,
    "burn_trend_percent": 6.8
}
```

#### Critical Alerts API
```python
# GET /api/v1/portfolio/alerts
{
    "critical_count": 3,
    "alerts": [
        {
            "id": "alert_001",
            "type": "budget_exceeded",
            "assignment_id": "project-delta",
            "message": "ProjectDelta over budget by $5K",
            "severity": "critical",
            "created_at": "2026-06-05T10:30:00Z"
        },
        {
            "id": "alert_002", 
            "type": "connector_down",
            "connector": "aws",
            "message": "AWS connector down for 2 hours",
            "severity": "critical",
            "created_at": "2026-06-05T08:30:00Z"
        }
    ]
}
```

#### Assignment Health Matrix API
```python
# GET /api/v1/assignments/health-matrix
{
    "assignments": [
        {
            "assignment_id": "project-alpha",
            "name": "Project Alpha",
            "health_score": 88,
            "attention_level": "healthy", 
            "monthly_burn": 8000,
            "burn_variance": -500,
            "team_size": 6,
            "trend": "improving",
            "risk_factors": []
        },
        {
            "assignment_id": "project-delta",
            "name": "Project Delta", 
            "health_score": 35,
            "attention_level": "critical",
            "monthly_burn": 18000,
            "burn_variance": 5000,
            "team_size": 12,
            "trend": "declining",
            "risk_factors": ["budget_exceeded", "deployment_failures", "team_burnout"]
        }
    ]
}
```

#### Connector Health API
```python
# GET /api/v1/connectors/health
{
    "overall_status": "degraded",
    "last_sync": "2026-06-05T14:27:00Z",
    "connectors": [
        {
            "type": "github",
            "status": "healthy",
            "last_success": "2026-06-05T14:25:00Z",
            "response_time_ms": 245,
            "assignments_connected": 8
        },
        {
            "type": "aws",
            "status": "down", 
            "last_success": "2026-06-05T12:30:00Z",
            "last_failure": "2026-06-05T14:25:00Z",
            "error_message": "Authentication failed",
            "assignments_affected": 6
        }
    ]
}
```

#### Recent Changes API
```python
# GET /api/v1/portfolio/changes?hours=24
{
    "changes": [
        {
            "event_type": "budget_change",
            "entity_type": "assignment", 
            "entity_id": "project-x",
            "change_description": "ProjectX budget increased 20%",
            "impact_level": "medium",
            "detected_at": "2026-06-05T13:45:00Z"
        },
        {
            "event_type": "team_change",
            "entity_type": "assignment",
            "entity_id": "client-y", 
            "change_description": "ClientY team size increased by 2",
            "impact_level": "low",
            "detected_at": "2026-06-05T11:20:00Z"
        }
    ]
}
```

### Background Jobs Required

#### Health Score Calculator
```python
# services/portfolio_health_service.py
class PortfolioHealthService:
    def calculate_assignment_health(self, workspace_id: str, assignment_id: str) -> int:
        """Calculate 0-100 health score for assignment"""
        # Weighted scoring algorithm
        
    def update_portfolio_snapshot(self, workspace_id: str) -> None:
        """Create portfolio health snapshot"""
        
    def detect_changes(self, workspace_id: str) -> List[dict]:
        """Detect significant changes since last check"""
```

#### Connector Monitor
```python
# services/connector_monitor_service.py  
class ConnectorMonitorService:
    def check_connector_health(self, workspace_id: str, assignment_id: str, connector_type: str) -> dict:
        """Test connector and update health status"""
        
    def run_health_checks(self) -> None:
        """Background job to test all connectors"""
```

---

## Component Hierarchy

### React Component Structure
```
PortfolioHealthDashboard/
├── CriticalAlertsHeader/
│   ├── AlertBanner.tsx
│   └── AlertList.tsx
├── HealthScoreCard/
│   ├── OverallScore.tsx
│   ├── ScoreTrend.tsx
│   └── HealthBreakdown.tsx
├── BurnTrajectoryCard/
│   ├── CurrentBurn.tsx
│   ├── TrendChart.tsx
│   └── RunwayCalculator.tsx
├── ConnectorHealthCard/
│   ├── ConnectorStatus.tsx
│   ├── SyncIndicator.tsx
│   └── HealthBadge.tsx
├── RecentChangesCard/
│   ├── ChangeEvent.tsx
│   ├── ChangeList.tsx
│   └── ImpactIndicator.tsx
└── AssignmentHealthMatrix/
    ├── AssignmentRow.tsx
    ├── HealthBadge.tsx
    ├── TrendIndicator.tsx
    └── ActionButtons.tsx
```

### HTML/JavaScript (Current Flask Template Approach)
```javascript
// template extensions for dashboard.html
function generatePortfolioHealthOverview(data) {
    return `
        ${generateCriticalAlerts(data.alerts)}
        ${generateHealthScoreCard(data.portfolio_health)}
        ${generateBurnTrajectory(data.burn_data)}
        ${generateConnectorHealth(data.connectors)}
        ${generateRecentChanges(data.changes)}
        ${generateAssignmentMatrix(data.assignments)}
    `;
}
```

---

## Attention Scoring Algorithm

### Health Score Calculation (0-100 scale)

#### Assignment-Level Health Score
```python
def calculate_assignment_health(assignment: dict) -> int:
    """
    Weighted health score calculation:
    - Financial Health: 40% weight
    - Operational Health: 35% weight  
    - Team Health: 25% weight
    """
    
    # Financial Health (0-100)
    financial_score = calculate_financial_health(
        actual_burn=assignment['monthly_burn'],
        target_burn=assignment['target_monthly_burn'],
        variance_threshold=0.15  # 15% variance acceptable
    )
    
    # Operational Health (0-100) 
    operational_score = calculate_operational_health(
        deployment_success_rate=assignment['deployment_success_rate'],
        connector_uptime=get_connector_uptime(assignment['id']),
        last_deployment_age=assignment['last_deployment_age_days']
    )
    
    # Team Health (0-100)
    team_score = calculate_team_health(
        velocity_trend=get_velocity_trend(assignment['id']),
        team_size_stability=get_team_size_stability(assignment['id'])
    )
    
    # Weighted calculation
    health_score = (
        financial_score * 0.40 +
        operational_score * 0.35 + 
        team_score * 0.25
    )
    
    return int(health_score)
```

#### Attention Level Classification
```python
def classify_attention_level(health_score: int, risk_factors: List[str]) -> str:
    """
    Classify assignment attention needs:
    - critical: 0-50 or has critical risk factors
    - at_risk: 51-75 or has warning risk factors  
    - healthy: 76-100 with no major risk factors
    """
    
    critical_risks = ['budget_exceeded', 'deployment_failures_critical', 'team_exodus']
    warning_risks = ['budget_variance_high', 'deployment_delays', 'velocity_declining']
    
    if health_score <= 50 or any(risk in critical_risks for risk in risk_factors):
        return 'critical'
    elif health_score <= 75 or any(risk in warning_risks for risk in risk_factors):
        return 'at_risk'
    else:
        return 'healthy'
```

#### Risk Factor Detection
```python
def detect_risk_factors(assignment: dict, metrics: dict) -> List[str]:
    """Identify specific risk factors for assignment"""
    risks = []
    
    # Financial risks
    if assignment['burn_variance_percent'] > 20:
        risks.append('budget_exceeded')
    elif assignment['burn_variance_percent'] > 10:
        risks.append('budget_variance_high')
    
    # Operational risks
    if metrics.get('deployment_success_rate', 100) < 70:
        risks.append('deployment_failures_critical')
    elif metrics.get('deployment_success_rate', 100) < 85:
        risks.append('deployment_delays')
    
    # Team risks
    if metrics.get('velocity_trend') == 'declining_fast':
        risks.append('velocity_declining')
    if metrics.get('team_turnover_30d', 0) > 2:
        risks.append('team_exodus')
        
    return risks
```

---

## Connector Health Monitoring

### Health Check Strategy

#### Connector Health States
- **Healthy** (🟢): Last successful sync within expected interval, response time normal
- **Degraded** (🟡): Delayed responses, occasional failures, but functional
- **Down** (🔴): Multiple consecutive failures, authentication issues, or timeouts

#### Health Check Implementation
```python
class ConnectorHealthChecker:
    """Monitor and assess connector health across all assignments"""
    
    async def check_connector_health(self, workspace_id: str, assignment_id: str, connector_type: str) -> dict:
        """Perform health check for specific connector"""
        start_time = time.time()
        
        try:
            # Attempt lightweight API call
            result = await self._test_connector_api(workspace_id, assignment_id, connector_type)
            response_time = int((time.time() - start_time) * 1000)
            
            # Update success metrics
            await self._record_success(workspace_id, assignment_id, connector_type, response_time)
            
            return {
                "status": "healthy" if response_time < 5000 else "degraded",
                "response_time_ms": response_time,
                "last_success": datetime.utcnow(),
                "error": None
            }
            
        except Exception as e:
            # Update failure metrics
            await self._record_failure(workspace_id, assignment_id, connector_type, str(e))
            
            # Determine status based on failure history
            failure_count = await self._get_consecutive_failures(workspace_id, assignment_id, connector_type)
            status = "down" if failure_count >= 3 else "degraded"
            
            return {
                "status": status,
                "error": str(e),
                "failure_count": failure_count,
                "last_failure": datetime.utcnow()
            }
    
    async def _test_connector_api(self, workspace_id: str, assignment_id: str, connector_type: str):
        """Perform connector-specific health test"""
        if connector_type == "github":
            # Test GitHub API with minimal call
            return await self._test_github_auth(workspace_id, assignment_id)
        elif connector_type == "jira":
            # Test Jira API connectivity  
            return await self._test_jira_auth(workspace_id, assignment_id)
        elif connector_type == "aws":
            # Test AWS credentials and basic service access
            return await self._test_aws_auth(workspace_id, assignment_id)
        # ... other connectors
```

#### Health Check Scheduling
```python
# Background job configuration
HEALTH_CHECK_INTERVALS = {
    "github": 300,    # 5 minutes
    "jira": 300,      # 5 minutes  
    "aws": 600,       # 10 minutes (slower API)
    "openai": 900     # 15 minutes
}

async def run_periodic_health_checks():
    """Background task to continuously monitor connector health"""
    checker = ConnectorHealthChecker()
    
    while True:
        assignments = await get_all_assignments_with_connectors()
        
        for assignment in assignments:
            for connector_type in assignment['enabled_connectors']:
                try:
                    await checker.check_connector_health(
                        assignment['workspace_id'],
                        assignment['assignment_id'],
                        connector_type
                    )
                except Exception as e:
                    logger.error(f"Health check failed for {connector_type}: {e}")
        
        # Sleep until next check cycle
        await asyncio.sleep(60)  # Check every minute, but respect individual intervals
```

---

## Portfolio Summary Approach

### Portfolio-Level Aggregation

#### Financial Portfolio Health
```python
class PortfolioFinancialHealth:
    """Calculate financial health metrics across all assignments"""
    
    def calculate_portfolio_burn_health(self, workspace_id: str) -> dict:
        """Assess overall portfolio financial health"""
        assignments = get_workspace_assignments(workspace_id)
        
        total_actual_burn = sum(a['monthly_burn'] for a in assignments)
        total_target_burn = sum(a.get('target_monthly_burn', a['monthly_burn']) for a in assignments)
        
        variance = total_actual_burn - total_target_burn
        variance_percent = (variance / total_target_burn) * 100 if total_target_burn > 0 else 0
        
        # Calculate trend based on last 3 months
        burn_history = get_portfolio_burn_history(workspace_id, months=3)
        trend_percent = calculate_burn_trend(burn_history)
        
        return {
            "total_monthly_burn": total_actual_burn,
            "budget_variance": variance,
            "variance_percent": variance_percent,
            "trend_percent": trend_percent,
            "health_score": self._calculate_financial_health_score(variance_percent, trend_percent)
        }
    
    def _calculate_financial_health_score(self, variance_percent: float, trend_percent: float) -> int:
        """Score financial health 0-100"""
        # Start with perfect score
        score = 100
        
        # Penalize budget variance
        if variance_percent > 20:
            score -= 40
        elif variance_percent > 10:
            score -= 20
        elif variance_percent > 5:
            score -= 10
            
        # Penalize negative trends
        if trend_percent > 15:
            score -= 30
        elif trend_percent > 10:
            score -= 15
            
        return max(0, score)
```

#### Operational Portfolio Health
```python
class PortfolioOperationalHealth:
    """Calculate operational health across all assignments and connectors"""
    
    def calculate_connector_portfolio_health(self, workspace_id: str) -> dict:
        """Assess overall connector health across portfolio"""
        connector_statuses = get_all_connector_health(workspace_id)
        
        total_connectors = len(connector_statuses)
        healthy_count = sum(1 for c in connector_statuses if c['status'] == 'healthy')
        degraded_count = sum(1 for c in connector_statuses if c['status'] == 'degraded')
        down_count = sum(1 for c in connector_statuses if c['status'] == 'down')
        
        # Calculate weighted health score
        health_score = (
            (healthy_count * 100) + 
            (degraded_count * 60) + 
            (down_count * 0)
        ) / total_connectors if total_connectors > 0 else 100
        
        return {
            "connector_health_score": int(health_score),
            "total_connectors": total_connectors,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "down_count": down_count,
            "critical_failures": [c for c in connector_statuses if c['status'] == 'down']
        }
```

#### Change Detection System
```python
class PortfolioChangeDetector:
    """Detect and track significant changes across portfolio"""
    
    def detect_significant_changes(self, workspace_id: str, hours: int = 24) -> List[dict]:
        """Find changes requiring CTO attention"""
        since_timestamp = datetime.utcnow() - timedelta(hours=hours)
        
        changes = []
        
        # Budget variance changes
        budget_changes = self._detect_budget_changes(workspace_id, since_timestamp)
        changes.extend(budget_changes)
        
        # Team composition changes
        team_changes = self._detect_team_changes(workspace_id, since_timestamp)
        changes.extend(team_changes)
        
        # Deployment patterns
        deployment_changes = self._detect_deployment_issues(workspace_id, since_timestamp) 
        changes.extend(deployment_changes)
        
        # Connector failures
        connector_changes = self._detect_connector_failures(workspace_id, since_timestamp)
        changes.extend(connector_changes)
        
        # Sort by impact level and recency
        changes.sort(key=lambda x: (
            {"high": 3, "medium": 2, "low": 1}[x.get("impact_level", "low")],
            x["detected_at"]
        ), reverse=True)
        
        return changes[:10]  # Return top 10 most significant
    
    def _detect_budget_changes(self, workspace_id: str, since: datetime) -> List[dict]:
        """Detect assignments with significant budget variance changes"""
        # Implementation to detect budget shifts
        pass
        
    def _detect_team_changes(self, workspace_id: str, since: datetime) -> List[dict]:
        """Detect team size or composition changes"""
        # Implementation to detect team changes
        pass
```

---

## Database Migration Strategy

### Migration Steps

#### Phase 1: Add Health Tracking Tables
```sql
-- Create new health tracking tables
-- (DDL statements from Data Model section above)
```

#### Phase 2: Extend Existing Tables
```sql
-- Add health fields to assignments table
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS health_score INTEGER DEFAULT 75;
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS attention_level TEXT DEFAULT 'healthy';
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP;
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS target_monthly_burn INTEGER;
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS deployment_success_rate DECIMAL(5,2);
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS last_deployment_at TIMESTAMP;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_assignments_health ON assignments(workspace_id, attention_level, health_score);
CREATE INDEX IF NOT EXISTS idx_connector_health_status ON connector_health_status(workspace_id, status, last_success);
CREATE INDEX IF NOT EXISTS idx_portfolio_changes ON portfolio_change_events(workspace_id, detected_at DESC, impact_level);
```

#### Phase 3: Populate Initial Data
```python
# services/migration/health_data_migration.py
class HealthDataMigration:
    """Populate initial health data for existing assignments"""
    
    def populate_initial_health_scores(self):
        """Calculate and populate health scores for existing assignments"""
        assignments = get_all_assignments()
        
        for assignment in assignments:
            # Calculate initial health score based on existing data
            health_score = self._calculate_initial_health_score(assignment)
            attention_level = self._classify_attention_level(health_score)
            
            # Update assignment with health data
            update_assignment_health(
                assignment['workspace_id'],
                assignment['assignment_id'], 
                health_score,
                attention_level
            )
```

### Backward Compatibility
- All new fields have sensible defaults
- Existing API endpoints continue to work unchanged
- New endpoints are additive only
- Health calculations gracefully handle missing data

---

## Implementation Priority

### Phase 1: Core Health Infrastructure (Week 1)
1. Create new database tables
2. Implement basic health score calculation
3. Add background health monitoring job
4. Create portfolio health service

### Phase 2: Dashboard UX (Week 2) 
1. Design critical alerts header
2. Implement portfolio health score card
3. Add burn trajectory visualization
4. Create connector health status display

### Phase 3: Intelligence Features (Week 3)
1. Implement change detection system
2. Add assignment health matrix
3. Create risk factor identification
4. Build trend analysis

### Phase 4: Polish & Optimization (Week 4)
1. Mobile responsive adjustments
2. Performance optimization
3. Alert notification system
4. Export and reporting features

---

## Success Metrics

### User Experience Metrics
- **Time to Critical Information:** < 30 seconds from dashboard load to identifying issues
- **Decision Accuracy:** Increase in proactive issue resolution before they become critical
- **Cognitive Load:** Reduced from information overload to actionable insights

### System Performance Metrics
- **Dashboard Load Time:** < 3 seconds for full portfolio health assessment
- **Data Freshness:** Health scores updated within 5 minutes of underlying changes
- **Connector Uptime:** 99%+ availability for health monitoring

### Business Impact Metrics
- **Budget Variance Detection:** Alert on budget overruns within 24 hours
- **Risk Identification:** Predict assignment issues 1-2 weeks before critical state
- **Portfolio Optimization:** Enable data-driven resource allocation decisions

---

This Portfolio Health Dashboard transforms the CTO Dashboard from a passive metrics display into an active operational intelligence platform, enabling Fractional CTOs to quickly assess portfolio health and make informed decisions about where to focus their limited time and attention.