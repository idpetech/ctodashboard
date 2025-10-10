# 🔧 Service Configuration - Detailed Implementation Plan

## 📋 Overview

**Goal:** Enable UI-based configuration of monitoring services (GitHub, Jira, OpenAI, Railway, AWS)

**Approach:** "Services First" - Build service management before workstream management

**Timeline:** 4-6 hours per service type

---

## 🎯 Phase 2.1: GitHub Service Configuration

### Scope
Allow users to configure GitHub monitoring through UI instead of editing JSON files.

### User Stories

**As a CTO, I want to:**
1. Add GitHub organization and repositories to monitor
2. Test GitHub connection before saving
3. Enable/disable GitHub monitoring with a toggle
4. View GitHub connection status
5. See which repos are being tracked

### UI Design (Text Mockup)

```
┌─────────────────────────────────────────────────────────┐
│ Service Configuration                            [Close] │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ┌─ GitHub Configuration ──────────────────────────────┐ │
│ │                                                      │ │
│ │ Enabled: [✓] Enable GitHub Monitoring               │ │
│ │                                                      │ │
│ │ Organization: [idpetech                         ]   │ │
│ │                                                      │ │
│ │ Repositories:                                        │ │
│ │ • [idpetech_portal              ] [Remove]          │ │
│ │ • [resumehealth-checker         ] [Remove]          │ │
│ │ [+ Add Repository]                                   │ │
│ │                                                      │ │
│ │ Track Deployments: [✓]                              │ │
│ │                                                      │ │
│ │ [Test Connection] [Save]                            │ │
│ │                                                      │ │
│ │ Status: ● Connected (2 repositories tracked)        │ │
│ └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### API Endpoints

```python
# GET /api/services/github/:workstream_id
# Get GitHub configuration for a workstream
{
  "enabled": true,
  "org": "idpetech",
  "repos": ["idpetech_portal", "resumehealth-checker"],
  "track_deployments": true
}

# POST /api/services/github/:workstream_id
# Update GitHub configuration
{
  "enabled": true,
  "org": "idpetech",
  "repos": ["new_repo"],
  "track_deployments": false
}

# POST /api/services/github/:workstream_id/test
# Test GitHub connection
{
  "status": "success",
  "repos_found": 2,
  "api_limit_remaining": 4998
}

# DELETE /api/services/github/:workstream_id
# Remove GitHub service
{
  "success": true,
  "message": "GitHub service removed"
}
```

### Implementation Steps

**Step 1: Backend API (2 hours)**
1. Create `services/github_service.py` 
2. Implement CRUD endpoints in routes
3. Add connection testing logic
4. Update assignment JSON on save

**Step 2: Frontend UI (2 hours)**
1. Add "Configure Services" button to each workstream
2. Create service configuration modal
3. Add GitHub form with validation
4. Implement test connection button

**Step 3: Integration (1 hour)**
1. Connect UI to API
2. Update existing metrics display
3. Add status indicators
4. Test thoroughly

**Step 4: Testing (1 hour)**
1. Test all CRUD operations
2. Test connection validation
3. Test error handling
4. Test with invalid tokens

### Data Flow

```
User clicks "Configure GitHub"
  ↓
Modal opens with current config
  ↓
User edits org/repos
  ↓
User clicks "Test Connection"
  ↓
API tests GitHub connection
  ↓
Shows success/failure
  ↓
User clicks "Save"
  ↓
API updates assignment JSON
  ↓
Metrics refresh with new config
```

### Error Handling

**Invalid Token:**
```
⚠️ GitHub connection failed
Invalid or expired token. Please check your GitHub token.
```

**API Rate Limit:**
```
⚠️ GitHub rate limit exceeded
Try again in 15 minutes or use a different token.
```

**Invalid Organization:**
```
⚠️ Organization not found
Please verify the organization name is correct.
```

### Success Criteria

- ✅ Can add/edit/remove GitHub config through UI
- ✅ Connection test works before saving
- ✅ Invalid config shows clear errors
- ✅ Changes persist to JSON file
- ✅ Metrics update with new config
- ✅ All existing functionality still works

---

## 📊 Phase 2.2-2.5: Other Services

### Jira Service (Similar to GitHub)
- Organization → Jira URL
- Repos → Project Keys
- Same CRUD pattern
- **Estimated:** 4 hours

### OpenAI Service
- API Key configuration
- Usage tracking toggle
- Cost monitoring toggle
- **Estimated:** 3 hours

### Railway Service
- Project ID configuration
- Deployment tracking
- Usage monitoring
- **Estimated:** 3 hours

### AWS Service
- Account ID
- Services to monitor
- Cost tracking toggle
- **Estimated:** 5 hours (most complex)

---

## 🏗️ Technical Architecture

### BaseService Pattern (DRY)

```python
class BaseService:
    """Base class for all service configurations"""
    
    def __init__(self, service_type: str):
        self.service_type = service_type
        
    def test_connection(self, config: dict) -> dict:
        """Test service connection - override in subclass"""
        raise NotImplementedError
    
    def save_config(self, workstream_id: str, config: dict):
        """Save configuration to assignment JSON"""
        # Load assignment
        # Update metrics_config
        # Save back to JSON
        
    def get_config(self, workstream_id: str) -> dict:
        """Get current configuration"""
        # Load from assignment JSON
        
class GitHubService(BaseService):
    def __init__(self):
        super().__init__("github")
    
    def test_connection(self, config: dict) -> dict:
        """Test GitHub connection"""
        # Try to fetch org
        # Verify token works
        # Return status
```

### Service Factory Pattern

```python
class ServiceFactory:
    @staticmethod
    def create_service(service_type: str):
        services = {
            "github": GitHubService,
            "jira": JiraService,
            "openai": OpenAIService,
            "railway": RailwayService,
            "aws": AWSService
        }
        return services.get(service_type)()
```

### Service Manager

```python
class ServiceConfigManager:
    """Manages all service configurations"""
    
    def __init__(self):
        self.factory = ServiceFactory()
    
    def configure_service(self, service_type, workstream_id, config):
        service = self.factory.create_service(service_type)
        return service.save_config(workstream_id, config)
    
    def test_service(self, service_type, config):
        service = self.factory.create_service(service_type)
        return service.test_connection(config)
```

---

## 🎨 UI Patterns

### Service Configuration Modal

**Location:** Each workstream card has "Configure Services" button

**Layout:**
- Tab per service (GitHub, Jira, OpenAI, etc.)
- Form fields specific to service
- Test connection button (validates before save)
- Save/Cancel buttons
- Status indicator (Connected/Disconnected/Error)

### Status Display

```html
<!-- Connected -->
<span class="text-green-600">● Connected</span>

<!-- Disconnected -->
<span class="text-gray-400">○ Not Configured</span>

<!-- Error -->
<span class="text-red-600">● Error</span>
```

---

## 🔒 Security Considerations

### API Tokens
- **Storage:** Environment variables (current)
- **Future:** Encrypted database per tenant
- **Validation:** Test before saving
- **Display:** Never show in UI (show *****)

### Access Control
- **Current:** Single user (CTO)
- **Future:** Role-based access
- **Feature Flag:** Behind service_config_ui flag

---

## 📦 Data Model

### Current (JSON Files)

```json
{
  "id": "ideptech",
  "metrics_config": {
    "github": {
      "enabled": true,
      "org": "idpetech",
      "repos": ["repo1", "repo2"],
      "track_deployments": true
    }
  }
}
```

### Future (Database)

```sql
CREATE TABLE service_configs (
  id UUID PRIMARY KEY,
  workstream_id UUID REFERENCES workstreams(id),
  service_type VARCHAR(50),
  enabled BOOLEAN,
  config JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## 🧪 Testing Strategy

### Unit Tests
```python
def test_github_service_save():
    service = GitHubService()
    config = {"org": "test", "repos": ["repo1"]}
    result = service.save_config("ideptech", config)
    assert result["success"] == True

def test_github_connection():
    service = GitHubService()
    config = {"org": "invalid"}
    result = service.test_connection(config)
    assert result["status"] == "error"
```

### Integration Tests
1. Create service config through UI
2. Test connection
3. Save config
4. Verify metrics update
5. Edit config
6. Delete config

### Manual Tests
1. Invalid token handling
2. Rate limit handling
3. Network error handling
4. UI responsiveness

---

## ⏱️ Time Estimates

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 2.1 | GitHub Service UI | 4-6 hours |
| 2.2 | Jira Service UI | 4 hours |
| 2.3 | OpenAI Service UI | 3 hours |
| 2.4 | Railway Service UI | 3 hours |
| 2.5 | AWS Service UI | 5 hours |
| **Total** | | **19-25 hours** |

---

## 🚧 Potential Risks

### Risk 1: API Rate Limits
**Issue:** Testing connections might hit GitHub/Jira API limits

**Mitigation:**
- Cache test results for 5 minutes
- Show "Test again in X minutes" message
- Use conditional requests (If-Modified-Since)

### Risk 2: Complex AWS Configuration
**Issue:** AWS has many services, complex configuration

**Mitigation:**
- Start with simple: Account ID only
- Add service selection in Phase 2.5.2
- Use AWS service categories

### Risk 3: Token Security
**Issue:** How to handle API tokens securely

**Mitigation:**
- Environment variables for now
- Future: Encrypted storage per tenant
- Never display full tokens in UI

---

## 📈 Success Metrics

### Functionality
- ✅ All 5 services configurable through UI
- ✅ Connection testing works for all
- ✅ Configuration persists correctly
- ✅ Metrics update with new config

### Quality
- ✅ Clean code following KISS/DRY/SOC
- ✅ Comprehensive error handling
- ✅ Validated before deployment
- ✅ Zero technical debt

### User Experience
- ✅ Intuitive UI
- ✅ Clear error messages
- ✅ Fast response times
- ✅ No broken states

---

## 🔄 Iteration Plan

### Iteration 1: GitHub Only (Week 1)
- Build complete GitHub service config
- Perfect the patterns
- Test thoroughly
- Deploy to production

### Iteration 2: Jira + OpenAI (Week 2)
- Reuse GitHub patterns
- Add service-specific fields
- Test integration
- Deploy

### Iteration 3: Railway + AWS (Week 3)
- Complete remaining services
- Polish UI
- Full integration testing
- Final deployment

---

## 📝 Open Questions for Discussion

1. **UI Location:**
   - Modal on workstream card?
   - Separate "Settings" page?
   - Inline on workstream detail page?

2. **Validation:**
   - Block save if connection fails?
   - Allow save with warning?
   - Require connection test before save?

3. **Storage:**
   - Keep JSON files?
   - Migrate to database now?
   - Hybrid approach?

4. **Scope:**
   - All services at once?
   - GitHub first, iterate?
   - Most important services first?

---

**This plan is ready for review and discussion when you return!** 📋

No code changes made - only planning and design.
