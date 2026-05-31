# Connector Architecture Refactoring Proposal

## 🚨 Current Problems

### Monolithic Structure:
```
routes/
  api_routes.py (1,690 lines!) - Everything mixed together
    - GitHub validation
    - AWS validation  
    - OpenAI validation
    - Jira validation
    - Route definitions
    - Business logic
    - Error handling
```

### Issues:
- **Violation of Single Responsibility Principle**
- **Hard to test individual connectors**
- **Difficult to add new connectors**
- **Mixed concerns** (routing + validation + business logic)
- **No code reusability**
- **Maintenance nightmare**

## ✅ Proposed Clean Architecture

### New Structure:
```
connectors/
  __init__.py
  base/
    __init__.py
    base_connector.py        # Abstract base class
    validation_mixin.py      # Common validation patterns
    exceptions.py            # Connector-specific exceptions
  
  github/
    __init__.py
    connector.py             # GitHubConnector class
    validator.py             # GitHub credential validation
    models.py                # GitHub data models
    exceptions.py            # GitHub-specific exceptions
  
  aws/
    __init__.py
    connector.py             # AWSConnector class  
    validator.py             # AWS credential validation
    models.py                # AWS data models
    exceptions.py            # AWS-specific exceptions
  
  openai/
    __init__.py
    connector.py             # OpenAIConnector class
    validator.py             # OpenAI credential validation
    models.py                # OpenAI data models
    exceptions.py            # OpenAI-specific exceptions
  
  jira/
    __init__.py
    connector.py             # JiraConnector class
    validator.py             # Jira credential validation
    models.py                # Jira data models
    exceptions.py            # Jira-specific exceptions

  registry.py                # Connector registry/factory
  utils.py                   # Common connector utilities
```

### Routes Structure:
```
routes/
  __init__.py
  auth_routes.py             # Authentication endpoints
  workspace_routes.py        # Workspace management
  connector_routes.py        # Connector configuration
  metrics_routes.py          # Metrics endpoints
  admin_routes.py            # Admin endpoints
  health_routes.py           # Health/status endpoints
```

## 🔧 Implementation Benefits

### 1. Single Responsibility
Each connector handles only its own logic:
```python
# connectors/github/connector.py
class GitHubConnector(BaseConnector):
    def __init__(self, workspace_id=None, assignment_id=None):
        super().__init__(workspace_id, assignment_id)
        
    def get_metrics(self, config: dict) -> dict:
        # GitHub-specific metrics logic
        
    def validate_credentials(self, credentials: dict) -> dict:
        # Use GitHubValidator
```

### 2. Easy Testing
```python
# tests/connectors/test_github.py
def test_github_connector():
    connector = GitHubConnector()
    result = connector.validate_credentials(mock_creds)
    assert result["valid"] == True
```

### 3. Plugin Architecture
```python
# connectors/registry.py
class ConnectorRegistry:
    _connectors = {
        "github": GitHubConnector,
        "aws": AWSConnector,
        "openai": OpenAIConnector,
        "jira": JiraConnector
    }
    
    @classmethod
    def get_connector(cls, connector_type, workspace_id=None, assignment_id=None):
        connector_class = cls._connectors.get(connector_type)
        if not connector_class:
            raise UnknownConnectorError(f"Unknown connector: {connector_type}")
        return connector_class(workspace_id, assignment_id)
```

### 4. Common Base Class
```python
# connectors/base/base_connector.py
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    def __init__(self, workspace_id=None, assignment_id=None):
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        self._init_credentials()
    
    @abstractmethod
    def get_metrics(self, config: dict) -> dict:
        pass
    
    @abstractmethod
    def validate_credentials(self, credentials: dict) -> dict:
        pass
    
    def _init_credentials(self):
        # Common credential loading logic
        pass
```

## 📦 Migration Strategy

### Phase 1: Extract Validators
1. Create `connectors/` package
2. Move validation functions to individual validator modules
3. Update imports in api_routes.py

### Phase 2: Extract Connectors  
1. Move connector classes to individual modules
2. Create base connector class
3. Update service integrations

### Phase 3: Split Routes
1. Break api_routes.py into logical route modules
2. Update route registration
3. Clean up imports

### Phase 4: Add Registry
1. Create connector registry/factory
2. Update all connector usage to use registry
3. Remove direct imports

## 🎯 End Result

### Before (Current):
- 1 file with 1,690 lines
- Mixed concerns
- Hard to test
- Difficult to extend

### After (Proposed):
- 20+ focused modules
- Clear separation of concerns  
- Easy unit testing
- Simple to add new connectors
- Plugin architecture ready for future expansion

## 🚀 Implementation Priority

1. **High Priority**: Extract validators (reduces immediate brittleness)
2. **Medium Priority**: Extract connector classes (improves testability)
3. **Low Priority**: Split routes (improves organization)
4. **Future**: Add plugin system (enables dynamic connector loading)