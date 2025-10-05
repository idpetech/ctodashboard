# 🏗️ MASTER ARCHITECTURE DOCUMENT (MAD)
## CTO Dashboard Platform - Single Source of Truth

### 🎯 **CORE PRINCIPLES (NEVER DEVIATE)**

1. **"Always Working" Principle**
   - Current functionality MUST NEVER break
   - Feature flags control new capabilities
   - Backward compatibility is MANDATORY
   - Zero-risk deployments only

2. **"Fake it while you make it" Philosophy**
   - Incremental feature delivery
   - Progressive enhancement
   - Graceful degradation
   - User opt-in to new features

3. **Single Service Architecture**
   - ONE Flask app (`integrated_dashboard.py`)
   - ONE deployment target (Railway)
   - ONE HTML template with embedded features
   - NO React, NO separate frontend/backend

4. **Consistency Requirements**
   - Same UI patterns across all features
   - Same API patterns across all endpoints
   - Same error handling across all services
   - Same styling approach (Tailwind CDN)

### 🏛️ **ARCHITECTURE LAYERS (EXACT ORDER)**

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              integrated_dashboard.py                   │ │
│  │  • Single Flask app                                    │ │
│  │  • HTML template with embedded JavaScript             │ │
│  │  • Tailwind CDN for styling                          │ │
│  │  • Feature flags for progressive enhancement         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  • LegacyAssignmentService (EXISTING - DO NOT TOUCH)   │ │
│  │  • SaaSAssignmentService (NEW - FEATURE FLAG CONTROLLED)│ │
│  │  • WorkstreamService (NEW - FEATURE FLAG CONTROLLED)   │ │
│  │  • ServiceConfigService (NEW - FEATURE FLAG CONTROLLED)│ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  • JSON files in backend/assignments/ (EXISTING)       │ │
│  │  • SQLite database (NEW - FEATURE FLAG CONTROLLED)     │ │
│  │  • File-based fallback (ALWAYS AVAILABLE)             │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 🔧 **IMPLEMENTATION STRATEGY (EXACT STEPS)**

#### **Phase 1: Foundation (Week 1)**
- [ ] Add feature flags to `integrated_dashboard.py`
- [ ] Create service layer structure
- [ ] Deploy with ALL flags disabled
- [ ] Verify existing functionality unchanged

#### **Phase 2: Workstream Management (Week 2)**
- [ ] Implement WorkstreamService
- [ ] Add workstream CRUD endpoints
- [ ] Add workstream UI components
- [ ] Enable workstream management flag
- [ ] Test thoroughly

#### **Phase 3: Service Configuration (Week 3)**
- [ ] Implement ServiceConfigService
- [ ] Add service config endpoints
- [ ] Add service config UI
- [ ] Enable service config flag
- [ ] Test thoroughly

#### **Phase 4: Multi-tenancy (Week 4)**
- [ ] Implement tenant management
- [ ] Add data isolation
- [ ] Enable multi-tenancy flag
- [ ] Test thoroughly

#### **Phase 5: Migration & Testing (Week 5)**
- [ ] Create migration tools
- [ ] Comprehensive testing
- [ ] Gradual rollout

### 📋 **FEATURE FLAGS (EXACT DEFINITION)**

```python
FEATURE_FLAGS = {
    "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
    "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true",
    "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true",
    "advanced_billing": os.getenv("ENABLE_BILLING", "false").lower() == "true",
    "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true"
}
```

### 🎨 **UI PATTERNS (EXACT TEMPLATES)**

#### **Card Pattern (ALL FEATURES)**
```html
<div class="bg-white rounded-lg shadow p-6 mb-6">
    <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold">{TITLE}</h2>
        <button onclick="{ACTION_FUNCTION}()" 
                class="bg-{COLOR}-600 text-white px-4 py-2 rounded hover:bg-{COLOR}-700">
            + {ACTION_TEXT}
        </button>
    </div>
    <div id="{CONTENT_ID}">
        <!-- Content will be loaded here -->
    </div>
</div>
```

#### **Modal Pattern (ALL FEATURES)**
```html
<div id="{MODAL_ID}" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 hidden">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl h-[80vh] flex flex-col">
        <!-- Header -->
        <div class="bg-{COLOR}-600 text-white p-4 rounded-t-lg flex justify-between items-center">
            <h3 class="text-lg font-semibold">{MODAL_TITLE}</h3>
            <button onclick="close{MODAL_NAME}()" class="text-white hover:text-gray-200">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-4">
            <!-- Modal content -->
        </div>
        <!-- Footer -->
        <div class="p-4 border-t">
            <div class="flex justify-end space-x-2">
                <button onclick="close{MODAL_NAME}()" class="px-4 py-2 text-gray-600 hover:text-gray-800">Cancel</button>
                <button onclick="save{MODAL_NAME}()" class="bg-{COLOR}-600 text-white px-4 py-2 rounded hover:bg-{COLOR}-700">Save</button>
            </div>
        </div>
    </div>
</div>
```

### 🔌 **API PATTERNS (EXACT STRUCTURE)**

#### **CRUD Endpoints (ALL FEATURES)**
```python
@app.route("/api/{resource}", methods=["GET", "POST"])
def {resource}_endpoint():
    if not FEATURE_FLAGS["{feature_flag}"]:
        return jsonify({"error": "Feature not enabled"}), 404
    
    if request.method == "GET":
        return get_{resource}()
    elif request.method == "POST":
        return create_{resource}()

@app.route("/api/{resource}/<{resource}_id>", methods=["GET", "PUT", "DELETE"])
def {resource}_detail({resource}_id):
    if not FEATURE_FLAGS["{feature_flag}"]:
        return jsonify({"error": "Feature not enabled"}), 404
    
    if request.method == "GET":
        return get_{resource}_by_id({resource}_id)
    elif request.method == "PUT":
        return update_{resource}({resource}_id)
    elif request.method == "DELETE":
        return delete_{resource}({resource}_id)
```

### 🚫 **FORBIDDEN ACTIONS (NEVER DO)**

1. **NEVER modify existing working code** without feature flags
2. **NEVER create duplicate functionality** - use existing patterns
3. **NEVER change UI patterns** - follow established templates
4. **NEVER break backward compatibility** - always maintain fallbacks
5. **NEVER deploy without feature flags** - always start disabled
6. **NEVER create new files** without updating this document
7. **NEVER change deployment target** - always use Railway
8. **NEVER use different styling** - always use Tailwind CDN

### ✅ **MANDATORY ACTIONS (ALWAYS DO)**

1. **ALWAYS check feature flags** before implementing new features
2. **ALWAYS follow established patterns** for UI and API
3. **ALWAYS maintain backward compatibility** with existing code
4. **ALWAYS test thoroughly** before enabling feature flags
5. **ALWAYS document changes** in this file
6. **ALWAYS use existing service patterns** for new features
7. **ALWAYS follow the exact implementation order** defined above

### 📊 **SUCCESS METRICS**

- [ ] Zero breaking changes to existing functionality
- [ ] All new features behind feature flags
- [ ] Consistent UI patterns across all features
- [ ] Consistent API patterns across all endpoints
- [ ] Successful deployment to Railway
- [ ] All feature flags working correctly
- [ ] Migration path from legacy to SaaS

### 🔄 **CHANGE MANAGEMENT**

1. **Any change MUST be documented here first**
2. **Any new feature MUST follow established patterns**
3. **Any UI change MUST use existing templates**
4. **Any API change MUST follow established structure**
5. **Any deployment MUST maintain backward compatibility**

---

## 🚨 **CRITICAL REMINDER**

**THIS DOCUMENT IS THE SINGLE SOURCE OF TRUTH**

- **Read this before making ANY changes**
- **Follow the exact patterns defined here**
- **Never deviate from the established approach**
- **Always maintain consistency with existing code**

**NO EXCEPTIONS. NO SHORTCUTS. NO TANGENTS.**
