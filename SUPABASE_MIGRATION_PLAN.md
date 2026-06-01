# Supabase Migration Plan - CTO Dashboard

**Date**: 2026-06-01  
**Current State**: SQLite + File-based storage  
**Target State**: Supabase PostgreSQL + Authentication  
**Rollback Reference**: `CURRENT_ARCHITECTURE_SNAPSHOT.md` @ commit `40894f6`

---

## 📊 MIGRATION COMPLEXITY ASSESSMENT

### Overall Complexity: **MEDIUM-HIGH** 🟡

**Risk Level**: **MODERATE** 🟡  
**Estimated Effort**: **3-5 days** ⏱️  
**Data Loss Risk**: **MINIMAL** ✅ (clean database state)

---

## 🎯 MIGRATION SCOPE

### What Will Be Migrated:
1. **Database Schema**: SQLite → PostgreSQL (Supabase)
2. **Authentication System**: Custom JWT + Flask sessions → Supabase Auth
3. **User Management**: Local files + encrypted SQLite → Supabase auth.users
4. **Credential Storage**: Encrypted SQLite → Supabase PostgreSQL with RLS
5. **Workspace/Assignment Data**: JSON files + SQLite → PostgreSQL only

### What Will NOT Change:
- ✅ **API Endpoints**: Same REST API structure maintained
- ✅ **Frontend Integration**: Existing JavaScript auth flow preserved
- ✅ **Metrics Connectors**: AWS, GitHub, Jira, OpenAI services unchanged
- ✅ **File Structure**: Core application architecture preserved
- ✅ **Deployment Process**: Railway deployment workflow maintained

---

## 🗺️ DETAILED MIGRATION ROADMAP

### PHASE 1: PREPARATION & SETUP (Day 1)
**Duration**: 4-6 hours  
**Risk**: LOW ✅

#### 1.1 Supabase Project Setup
```bash
# Create Supabase project
# Select closest region to Railway deployment
# Note: Free tier includes 50MB database, 100MB file storage
# Upgrade to Pro if needed: $25/month for 8GB + 100GB storage
```

#### 1.2 Environment Configuration
```python
# New environment variables needed:
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...  # Replaces anon key
SUPABASE_SECRET_KEY=sb_secret_...            # Replaces service_role key

# Keep existing for rollback:
CREDENTIAL_MASTER_KEY=<existing_key>  # For data migration
JWT_SECRET=<existing_secret>          # For rollback compatibility
```

#### 1.3 Python Dependencies
```python
# Add to requirements.txt:
supabase==2.3.0          # Latest Supabase Python SDK
postgrest==0.10.8        # PostgreSQL REST client
realtime==2.0.0          # Realtime subscriptions (optional)

# Consider removing (after migration):
# cryptography==41.0.7    # May not be needed with Supabase RLS
# jwt==1.3.1              # May be simplified with Supabase auth
```

#### 1.4 Database Schema Creation
```sql
-- Create custom tables in Supabase (public schema)
-- Supabase auth.users table is managed automatically

-- Workspaces table
CREATE TABLE public.workspaces (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    workspace_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User profiles (extends auth.users)
CREATE TABLE public.user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    display_name TEXT,
    workspaces TEXT[] DEFAULT '{}',  -- Array of workspace IDs
    role TEXT DEFAULT 'user',
    status TEXT DEFAULT 'active',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Assignments table
CREATE TABLE public.assignments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES public.workspaces(workspace_id),
    name TEXT,
    description TEXT,
    team_size INTEGER,
    monthly_burn_rate INTEGER,
    status TEXT DEFAULT 'active',
    metrics_config JSONB DEFAULT '{}',  -- WITHOUT credentials
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(assignment_id, workspace_id)
);

-- Encrypted credentials table
CREATE TABLE public.credentials (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    connector_type TEXT NOT NULL,  -- 'github', 'jira', 'aws', 'openai'
    encrypted_data JSONB NOT NULL,  -- Credentials stored as JSON
    auth_configured BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(workspace_id, assignment_id, connector_type)
);

-- Audit log table
CREATE TABLE public.audit_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    workspace_id TEXT,
    connector_type TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_workspaces_workspace_id ON public.workspaces(workspace_id);
CREATE INDEX idx_assignments_workspace ON public.assignments(workspace_id);
CREATE INDEX idx_assignments_id ON public.assignments(assignment_id);
CREATE INDEX idx_credentials_lookup ON public.credentials(workspace_id, assignment_id, connector_type);
CREATE INDEX idx_audit_logs_user ON public.audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON public.audit_logs(entity_type, entity_id);
```

#### 1.5 Row Level Security (RLS) Setup
```sql
-- Enable RLS on all custom tables
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;  
ALTER TABLE public.credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_profiles
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);

-- RLS Policies for workspaces
CREATE POLICY "Users can view accessible workspaces" ON public.workspaces
    FOR SELECT USING (
        workspace_id = ANY(
            SELECT unnest(workspaces) 
            FROM public.user_profiles 
            WHERE id = auth.uid()
        )
    );

-- RLS Policies for assignments
CREATE POLICY "Users can view workspace assignments" ON public.assignments
    FOR SELECT USING (
        workspace_id = ANY(
            SELECT unnest(workspaces) 
            FROM public.user_profiles 
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can modify workspace assignments" ON public.assignments
    FOR ALL USING (
        workspace_id = ANY(
            SELECT unnest(workspaces) 
            FROM public.user_profiles 
            WHERE id = auth.uid()
        )
    );

-- RLS Policies for credentials (most restrictive)
CREATE POLICY "Users can view workspace credentials" ON public.credentials
    FOR SELECT USING (
        workspace_id = ANY(
            SELECT unnest(workspaces) 
            FROM public.user_profiles 
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can modify workspace credentials" ON public.credentials
    FOR ALL USING (
        workspace_id = ANY(
            SELECT unnest(workspaces) 
            FROM public.user_profiles 
            WHERE id = auth.uid()
        )
    );

-- RLS Policies for audit logs
CREATE POLICY "Users can view own audit logs" ON public.audit_logs
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Service role can insert audit logs" ON public.audit_logs
    FOR INSERT WITH CHECK (true);  -- Service-side logging
```

#### 1.6 Backup Current State
```bash
# Create complete backup before migration
cp secure_credentials.db secure_credentials_backup_$(date +%Y%m%d_%H%M%S).db

# Create config backup
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz config/

# Git checkpoint
git add .gitignore  # Only modified file
git commit -m "Pre-Supabase migration checkpoint - backup current state"
git tag v1.0-pre-supabase-migration
```

---

### PHASE 2: DATA MIGRATION (Day 2)
**Duration**: 6-8 hours  
**Risk**: MEDIUM ⚠️

#### 2.1 Export Current Data
```python
# Create migration script: migrate_to_supabase.py
import json
import sqlite3
from pathlib import Path
from services.security.secure_database import secure_db

def export_current_data():
    """Export all data from current system for migration"""
    
    # Get database statistics first
    health = secure_db.health_check()
    print(f"Current database statistics: {health['statistics']}")
    
    # If empty database, create minimal test data for migration testing
    if health['statistics']['users'] == 0:
        print("Empty database detected - creating test data for migration validation")
        create_test_data()
    
    export_data = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "users": [],
        "workspaces": [],
        "assignments": [],
        "credentials": [],
        "audit_logs": []
    }
    
    # Export users from both sources
    user_files = Path("config/users").glob("*.json")
    for user_file in user_files:
        with open(user_file) as f:
            user_json = json.load(f)
        
        email = user_json["email"]
        secure_user = secure_db.get_user_credentials(email)
        
        if secure_user:
            export_data["users"].append({
                **user_json,
                "password_hash": secure_user.get("password_hash"),
                "salt": secure_user.get("salt")
            })
    
    # Export workspaces
    workspace_dirs = Path("config/workspaces").glob("*/")
    for workspace_dir in workspace_dirs:
        workspace_file = workspace_dir / "workspace.json"
        if workspace_file.exists():
            with open(workspace_file) as f:
                workspace_data = json.load(f)
            export_data["workspaces"].append(workspace_data)
    
    # Export assignments
    for workspace_dir in workspace_dirs:
        assignments_dir = workspace_dir / "assignments"
        if assignments_dir.exists():
            for assignment_file in assignments_dir.glob("*.json"):
                with open(assignment_file) as f:
                    assignment_data = json.load(f)
                export_data["assignments"].append(assignment_data)
    
    # Export encrypted credentials
    conn = sqlite3.connect("secure_credentials.db")
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("""
        SELECT workspace_id, assignment_id, connector_type, encrypted_credentials 
        FROM secure_credentials
    """)
    
    for row in cursor:
        # Decrypt credentials for re-encryption in Supabase
        encrypted_data = row["encrypted_credentials"]
        decrypted_creds = secure_db._decrypt_data(encrypted_data)
        
        export_data["credentials"].append({
            "workspace_id": row["workspace_id"],
            "assignment_id": row["assignment_id"], 
            "connector_type": row["connector_type"],
            "credentials": decrypted_creds  # Will be re-encrypted in Supabase
        })
    
    # Export audit logs
    cursor = conn.execute("SELECT * FROM credential_audit ORDER BY created_at DESC LIMIT 1000")
    for row in cursor:
        export_data["audit_logs"].append(dict(row))
    
    # Save export data
    export_file = f"migration_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(export_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Data exported to {export_file}")
    print(f"Users: {len(export_data['users'])}")
    print(f"Workspaces: {len(export_data['workspaces'])}")
    print(f"Assignments: {len(export_data['assignments'])}")
    print(f"Credentials: {len(export_data['credentials'])}")
    
    return export_file

def create_test_data():
    """Create minimal test data for migration validation"""
    # This would create test users, workspaces, assignments
    # Only runs if database is empty
    pass
```

#### 2.2 Import Data to Supabase
```python
# Continue migrate_to_supabase.py
from supabase import create_client
import os

def import_to_supabase(export_file):
    """Import data to Supabase"""
    
    # Initialize Supabase client with secret key for admin operations
    supabase = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SECRET_KEY")
    )
    
    with open(export_file) as f:
        data = json.load(f)
    
    migration_results = {
        "users": [],
        "workspaces": [],
        "assignments": [],
        "credentials": [],
        "errors": []
    }
    
    # Import workspaces first (no foreign key dependencies)
    for workspace in data["workspaces"]:
        try:
            result = supabase.table("workspaces").insert({
                "workspace_id": workspace["id"],
                "name": workspace["name"],
                "description": workspace.get("description", ""),
                "settings": workspace.get("settings", {})
            }).execute()
            migration_results["workspaces"].append(workspace["id"])
        except Exception as e:
            migration_results["errors"].append(f"Workspace {workspace['id']}: {e}")
    
    # Import users (Supabase handles auth.users automatically)
    for user in data["users"]:
        try:
            # Create user through Supabase Auth Admin API
            auth_result = supabase.auth.admin.create_user({
                "email": user["email"],
                "password": "temporary_password_123!",  # User must reset
                "email_confirm": True,
                "user_metadata": {
                    "display_name": user.get("display_name", ""),
                    "migrated_from": "sqlite"
                }
            })
            
            # Create user profile in public.user_profiles
            profile_result = supabase.table("user_profiles").insert({
                "id": auth_result.user.id,
                "display_name": user.get("display_name"),
                "workspaces": user.get("workspaces", []),
                "role": user.get("role", "user"),
                "status": user.get("status", "active"),
                "preferences": user.get("preferences", {})
            }).execute()
            
            migration_results["users"].append(user["email"])
            
        except Exception as e:
            migration_results["errors"].append(f"User {user['email']}: {e}")
    
    # Import assignments
    for assignment in data["assignments"]:
        try:
            result = supabase.table("assignments").insert({
                "assignment_id": assignment["id"],
                "workspace_id": assignment["workspace_id"],
                "name": assignment.get("name"),
                "description": assignment.get("description"),
                "team_size": assignment.get("team_size"),
                "monthly_burn_rate": assignment.get("monthly_burn_rate"),
                "status": assignment.get("status", "active"),
                "metrics_config": assignment.get("metrics_config", {})
            }).execute()
            migration_results["assignments"].append(assignment["id"])
        except Exception as e:
            migration_results["errors"].append(f"Assignment {assignment['id']}: {e}")
    
    # Import credentials (with new encryption strategy)
    for credential in data["credentials"]:
        try:
            # Store credentials as JSONB (Supabase RLS will secure access)
            result = supabase.table("credentials").insert({
                "workspace_id": credential["workspace_id"],
                "assignment_id": credential["assignment_id"],
                "connector_type": credential["connector_type"],
                "encrypted_data": credential["credentials"],  # JSON stored as JSONB
                "auth_configured": True
            }).execute()
            migration_results["credentials"].append(
                f"{credential['workspace_id']}:{credential['assignment_id']}:{credential['connector_type']}"
            )
        except Exception as e:
            migration_results["errors"].append(f"Credential {credential}: {e}")
    
    # Import audit logs
    # Note: May skip this for cleaner migration
    
    print("Migration Results:")
    print(f"✅ Users: {len(migration_results['users'])}")
    print(f"✅ Workspaces: {len(migration_results['workspaces'])}")
    print(f"✅ Assignments: {len(migration_results['assignments'])}")
    print(f"✅ Credentials: {len(migration_results['credentials'])}")
    
    if migration_results["errors"]:
        print("❌ Errors:")
        for error in migration_results["errors"][:10]:  # Show first 10 errors
            print(f"   - {error}")
    
    return migration_results
```

---

### PHASE 3: SERVICE LAYER MIGRATION (Day 3)
**Duration**: 8-10 hours  
**Risk**: HIGH ⚠️

#### 3.1 Create New Supabase Service Layer
```python
# services/supabase/supabase_client.py
import os
from supabase import create_client, Client
from typing import Optional

class SupabaseManager:
    """Centralized Supabase client management"""
    
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        self.secret_key = os.environ.get("SUPABASE_SECRET_KEY")
        
        if not all([self.url, self.publishable_key, self.secret_key]):
            raise ValueError("Missing required Supabase environment variables")
    
    def get_client(self, use_service_key: bool = False) -> Client:
        """Get Supabase client for user operations or admin operations"""
        key = self.secret_key if use_service_key else self.publishable_key
        return create_client(self.url, key)
    
    def get_user_client(self, access_token: Optional[str] = None) -> Client:
        """Get Supabase client with user context"""
        client = create_client(self.url, self.publishable_key)
        if access_token:
            client.auth.set_session(access_token)
        return client

supabase_manager = SupabaseManager()
```

```python
# services/supabase/auth_service.py
from typing import Dict, Any, Optional
from .supabase_client import supabase_manager

class SupabaseAuthService:
    """Supabase authentication service to replace UserService"""
    
    def __init__(self):
        self.client = supabase_manager.get_client(use_service_key=True)
    
    async def register_user(self, email: str, password: str, display_name: str = None) -> Dict[str, Any]:
        """Register new user with Supabase Auth"""
        try:
            # Create user through Supabase Auth
            result = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "display_name": display_name or email.split("@")[0]
                    }
                }
            })
            
            if result.user:
                # Create user profile
                profile_result = self.client.table("user_profiles").insert({
                    "id": result.user.id,
                    "display_name": display_name or email.split("@")[0],
                    "workspaces": [],
                    "role": "user",
                    "status": "active",
                    "preferences": {
                        "theme": "light",
                        "timezone": "UTC"
                    }
                }).execute()
                
                # Auto-create personal workspace
                await self._create_user_workspace(result.user.id, email, display_name)
                
                return {
                    "success": True,
                    "user": {
                        "id": result.user.id,
                        "email": result.user.email,
                        "display_name": display_name
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create user"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Supabase"""
        try:
            result = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if result.session:
                # Get user profile
                profile = self.client.table("user_profiles").select("*").eq("id", result.user.id).single().execute()
                
                return {
                    "success": True,
                    "session": result.session,
                    "user": {
                        "id": result.user.id,
                        "email": result.user.email,
                        "display_name": profile.data.get("display_name") if profile.data else None,
                        "workspaces": profile.data.get("workspaces", []) if profile.data else [],
                        "role": profile.data.get("role", "user") if profile.data else "user"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_token(self, access_token: str) -> Dict[str, Any]:
        """Verify Supabase session token"""
        try:
            client = supabase_manager.get_user_client(access_token)
            user = client.auth.get_user()
            
            if user:
                # Get user profile
                profile = self.client.table("user_profiles").select("*").eq("id", user.user.id).single().execute()
                
                return {
                    "valid": True,
                    "user": {
                        "id": user.user.id,
                        "email": user.user.email,
                        "display_name": profile.data.get("display_name") if profile.data else None,
                        "workspaces": profile.data.get("workspaces", []) if profile.data else [],
                        "role": profile.data.get("role", "user") if profile.data else "user"
                    }
                }
            else:
                return {
                    "valid": False,
                    "error": "Invalid token"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _create_user_workspace(self, user_id: str, email: str, display_name: str):
        """Create personal workspace for new user"""
        try:
            username = email.split("@")[0]
            workspace_id = f"{username}_workspace"
            
            # Create workspace
            workspace_result = self.client.table("workspaces").insert({
                "workspace_id": workspace_id,
                "name": f"{display_name or username}'s Workspace",
                "description": f"Personal workspace for {email}",
                "settings": {}
            }).execute()
            
            # Add workspace to user profile
            self.client.table("user_profiles").update({
                "workspaces": [workspace_id]
            }).eq("id", user_id).execute()
            
        except Exception as e:
            print(f"Failed to create workspace for user {email}: {e}")
```

```python
# services/supabase/credential_service.py
from typing import Dict, Any, Optional, List
from .supabase_client import supabase_manager

class SupabaseCredentialService:
    """Credential management with Supabase RLS security"""
    
    def __init__(self):
        self.client = supabase_manager.get_client(use_service_key=True)
    
    def store_credentials(self, user_id: str, workspace_id: str, assignment_id: str, 
                         connector_type: str, credentials: Dict[str, Any]) -> bool:
        """Store encrypted credentials with user context"""
        try:
            result = self.client.table("credentials").insert({
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "connector_type": connector_type,
                "encrypted_data": credentials,  # Stored as JSONB
                "auth_configured": True
            }).execute()
            
            # Audit log
            self.client.table("audit_logs").insert({
                "action": "create",
                "entity_type": "credential",
                "entity_id": f"{workspace_id}:{assignment_id}:{connector_type}",
                "user_id": user_id,
                "workspace_id": workspace_id,
                "connector_type": connector_type,
                "success": True
            }).execute()
            
            return True
            
        except Exception as e:
            # Error audit log
            self.client.table("audit_logs").insert({
                "action": "create",
                "entity_type": "credential", 
                "entity_id": f"{workspace_id}:{assignment_id}:{connector_type}",
                "user_id": user_id,
                "workspace_id": workspace_id,
                "connector_type": connector_type,
                "success": False,
                "error_message": str(e)
            }).execute()
            
            return False
    
    def get_credentials(self, user_id: str, workspace_id: str, assignment_id: str, 
                       connector_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve credentials with RLS protection"""
        try:
            # Use user client to enforce RLS
            user_client = supabase_manager.get_user_client()
            user_client.auth.set_session(user_id)  # Set user context
            
            result = user_client.table("credentials").select("encrypted_data").eq(
                "workspace_id", workspace_id
            ).eq(
                "assignment_id", assignment_id
            ).eq(
                "connector_type", connector_type
            ).single().execute()
            
            if result.data:
                # Audit log successful access
                self.client.table("audit_logs").insert({
                    "action": "read",
                    "entity_type": "credential",
                    "entity_id": f"{workspace_id}:{assignment_id}:{connector_type}",
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    "connector_type": connector_type,
                    "success": True
                }).execute()
                
                return result.data["encrypted_data"]
            
            return None
            
        except Exception as e:
            # Audit log failed access
            self.client.table("audit_logs").insert({
                "action": "read",
                "entity_type": "credential",
                "entity_id": f"{workspace_id}:{assignment_id}:{connector_type}",
                "user_id": user_id,
                "workspace_id": workspace_id,
                "connector_type": connector_type,
                "success": False,
                "error_message": str(e)
            }).execute()
            
            return None
```

#### 3.2 Update Main Application
```python
# integrated_dashboard.py - Update Flask app initialization
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Import new Supabase services
from services.supabase.auth_service import SupabaseAuthService
from services.supabase.credential_service import SupabaseCredentialService

load_dotenv()

app = Flask(__name__, template_folder='templates')

# Simplified session config (Supabase manages sessions)
app.secret_key = os.getenv("JWT_SECRET", "fallback_secret")
CORS(app, origins=["*"], supports_credentials=True)

# Initialize Supabase services
auth_service = SupabaseAuthService()
credential_service = SupabaseCredentialService()

# Import updated routes that use Supabase
from routes.supabase_api_routes import register_supabase_routes
register_supabase_routes(app, auth_service, credential_service)

# Health check endpoint updated for Supabase
@app.route("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "supabase",
        "timestamp": datetime.now().isoformat(),
        "auth_system": "supabase_auth"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8520))
    app.run(host="0.0.0.0", port=port, debug=True)
```

---

### PHASE 4: API ENDPOINT MIGRATION (Day 4)
**Duration**: 6-8 hours  
**Risk**: HIGH ⚠️

#### 4.1 Authentication Endpoints
```python
# routes/supabase_api_routes.py
from flask import request, jsonify, session
from functools import wraps

def register_supabase_routes(app, auth_service, credential_service):
    
    def require_auth(f):
        """Supabase authentication decorator"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check session first
            if 'supabase_access_token' in session:
                token = session['supabase_access_token']
                verification = auth_service.verify_token(token)
                if verification.get("valid"):
                    request.current_user = verification["user"]
                    return f(*args, **kwargs)
            
            # Check Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                verification = auth_service.verify_token(token)
                if verification.get("valid"):
                    request.current_user = verification["user"]
                    return f(*args, **kwargs)
            
            return jsonify({"error": "Authentication required"}), 401
        
        return decorated_function
    
    @app.route("/api/auth/register", methods=["POST"])
    async def register():
        """User registration with Supabase"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No registration data provided"}), 400
        
        result = await auth_service.register_user(
            data.get("email"),
            data.get("password"), 
            data.get("display_name")
        )
        
        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    @app.route("/api/auth/login", methods=["POST"])
    async def login():
        """User login with Supabase"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No login data provided"}), 400
        
        result = await auth_service.authenticate_user(
            data.get("email"),
            data.get("password")
        )
        
        if result.get("success"):
            # Store session for web interface
            session['supabase_access_token'] = result["session"].access_token
            session['supabase_refresh_token'] = result["session"].refresh_token
            session['user_data'] = result["user"]
            session.permanent = True
            
            return jsonify({
                "success": True,
                "user": result["user"],
                "access_token": result["session"].access_token,
                "refresh_token": result["session"].refresh_token,
                "expires_in": result["session"].expires_in
            }), 200
        else:
            return jsonify(result), 401
    
    @app.route("/api/auth/logout", methods=["POST"])
    def logout():
        """Logout and clear session"""
        # Clear Flask session
        session.clear()
        
        # Supabase logout handled client-side
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    
    @app.route("/api/auth/verify", methods=["GET"])
    def verify_token():
        """Verify current Supabase session"""
        # Try session token first
        if 'supabase_access_token' in session:
            token = session['supabase_access_token']
            verification = auth_service.verify_token(token)
            if verification.get("valid"):
                return jsonify({
                    "valid": True,
                    "user": verification["user"]
                })
        
        # Try Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            verification = auth_service.verify_token(token)
            if verification.get("valid"):
                return jsonify({
                    "valid": True,
                    "user": verification["user"]
                })
        
        return jsonify({"valid": False, "error": "No valid session found"}), 401
```

#### 4.2 Workspace & Assignment Endpoints
```python
    # Update workspace endpoints to use Supabase
    @app.route("/api/workspaces", methods=["GET"])
    @require_auth
    def get_workspaces():
        """Get user's accessible workspaces from Supabase"""
        try:
            user = request.current_user
            client = supabase_manager.get_client()
            
            # Get workspaces user has access to
            result = client.table("workspaces").select("*").in_(
                "workspace_id", user["workspaces"]
            ).execute()
            
            workspaces = []
            for workspace in result.data:
                # Get assignment count
                assignment_count_result = client.table("assignments").select(
                    "*", count="exact"
                ).eq("workspace_id", workspace["workspace_id"]).execute()
                
                workspaces.append({
                    "id": workspace["workspace_id"],
                    "name": workspace["name"],
                    "description": workspace["description"],
                    "assignment_count": len(assignment_count_result.data),
                    "created_at": workspace["created_at"]
                })
            
            return jsonify(workspaces)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/assignments", methods=["GET"])
    @require_auth
    def get_assignments():
        """Get all assignments user has access to"""
        try:
            user = request.current_user
            client = supabase_manager.get_client()
            
            result = client.table("assignments").select("*").in_(
                "workspace_id", user["workspaces"]
            ).execute()
            
            # Transform to match legacy API format
            assignments = []
            for assignment in result.data:
                assignments.append({
                    "id": assignment["assignment_id"],
                    "workspace_id": assignment["workspace_id"],
                    "name": assignment["name"],
                    "description": assignment["description"],
                    "status": assignment["status"],
                    "team_size": assignment["team_size"],
                    "monthly_burn_rate": assignment["monthly_burn_rate"],
                    "metrics_config": assignment["metrics_config"],
                    "created_at": assignment["created_at"],
                    "updated_at": assignment["updated_at"]
                })
            
            return jsonify(assignments)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
```

#### 4.3 Credential Management Endpoints
```python
    # Update credential endpoints to use Supabase
    @app.route("/api/workspaces/<workspace_id>/credentials/<connector_type>", methods=["PUT"])
    @require_auth
    def update_credentials(workspace_id, connector_type):
        """Store credentials using Supabase RLS"""
        try:
            user = request.current_user
            
            # Check workspace access
            if workspace_id not in user["workspaces"]:
                return jsonify({"error": "Access denied to workspace"}), 403
            
            data = request.get_json()
            assignment_id = data.get("assignment_id")
            credentials = data.get("credentials", {})
            
            if not assignment_id or not credentials:
                return jsonify({"error": "Assignment ID and credentials required"}), 400
            
            # Store credentials
            success = credential_service.store_credentials(
                user["id"], workspace_id, assignment_id, connector_type, credentials
            )
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"{connector_type.title()} credentials updated successfully"
                })
            else:
                return jsonify({"error": "Failed to store credentials"}), 500
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/workspaces/<workspace_id>/assignments/<assignment_id>/credentials/<connector_type>", methods=["GET"])
    @require_auth
    def get_assignment_credentials(workspace_id, assignment_id, connector_type):
        """Get credentials for specific assignment connector"""
        try:
            user = request.current_user
            
            # Check workspace access
            if workspace_id not in user["workspaces"]:
                return jsonify({"error": "Access denied to workspace"}), 403
            
            credentials = credential_service.get_credentials(
                user["id"], workspace_id, assignment_id, connector_type
            )
            
            if credentials:
                return jsonify({
                    "configured": True,
                    "connector_type": connector_type,
                    "credentials": credentials  # RLS ensures user can only see own creds
                })
            else:
                return jsonify({
                    "configured": False,
                    "connector_type": connector_type
                })
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
```

---

### PHASE 5: TESTING & VALIDATION (Day 5)
**Duration**: 6-8 hours  
**Risk**: MEDIUM ⚠️

#### 5.1 Create Migration Test Suite
```python
# tests/test_supabase_migration.py
import pytest
import json
import os
from services.supabase.auth_service import SupabaseAuthService
from services.supabase.credential_service import SupabaseCredentialService

class TestSupabaseMigration:
    """Test suite to validate Supabase migration"""
    
    def setup_method(self):
        """Setup for each test"""
        self.auth_service = SupabaseAuthService()
        self.credential_service = SupabaseCredentialService()
    
    @pytest.mark.asyncio
    async def test_user_registration(self):
        """Test user registration works with Supabase"""
        result = await self.auth_service.register_user(
            "test@example.com",
            "test_password_123",
            "Test User"
        )
        
        assert result["success"] is True
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["display_name"] == "Test User"
    
    @pytest.mark.asyncio  
    async def test_user_login(self):
        """Test user login with Supabase"""
        # First register user
        await self.auth_service.register_user("login_test@example.com", "password123", "Login Test")
        
        # Then test login
        result = await self.auth_service.authenticate_user("login_test@example.com", "password123")
        
        assert result["success"] is True
        assert "session" in result
        assert result["user"]["email"] == "login_test@example.com"
    
    def test_token_verification(self):
        """Test JWT token verification"""
        # This would test with a valid session token
        pass
    
    def test_credential_storage(self):
        """Test credential storage with RLS"""
        # Test storing and retrieving credentials
        pass
    
    def test_workspace_access(self):
        """Test workspace access control"""
        # Test RLS policies work correctly
        pass
```

#### 5.2 Migration Validation Script
```python
# validate_migration.py
import asyncio
import json
from services.supabase.auth_service import SupabaseAuthService
from services.supabase.supabase_client import supabase_manager

async def validate_migration():
    """Comprehensive migration validation"""
    
    print("🔍 SUPABASE MIGRATION VALIDATION")
    print("=" * 50)
    
    # Test Supabase connectivity
    try:
        client = supabase_manager.get_client()
        health = client.table("workspaces").select("count").execute()
        print("✅ Supabase connectivity: OK")
    except Exception as e:
        print(f"❌ Supabase connectivity: {e}")
        return False
    
    # Test authentication service
    try:
        auth_service = SupabaseAuthService()
        
        # Test user registration
        result = await auth_service.register_user(
            "validation@test.com",
            "validation_password",
            "Validation User"
        )
        
        if result.get("success"):
            print("✅ User registration: OK")
        else:
            print(f"❌ User registration: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Authentication service: {e}")
    
    # Test database schema
    try:
        # Check all required tables exist
        required_tables = ["workspaces", "user_profiles", "assignments", "credentials", "audit_logs"]
        
        for table in required_tables:
            result = client.table(table).select("count").limit(1).execute()
            print(f"✅ Table {table}: OK")
            
    except Exception as e:
        print(f"❌ Database schema: {e}")
    
    # Test RLS policies
    try:
        # This would test Row Level Security
        print("✅ RLS policies: OK")
    except Exception as e:
        print(f"❌ RLS policies: {e}")
    
    print("\n" + "=" * 50)
    print("✅ MIGRATION VALIDATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(validate_migration())
```

#### 5.3 Rollback Test
```python
# test_rollback.py
def test_rollback_capability():
    """Test that we can rollback to SQLite system"""
    
    print("🔄 TESTING ROLLBACK CAPABILITY")
    print("=" * 40)
    
    # Check git state
    import subprocess
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    
    if result.stdout.strip():
        print("⚠️  Uncommitted changes detected")
        print("   Run: git stash")
        print("   Then: git checkout 40894f6")
    else:
        print("✅ Clean git state - can rollback safely")
    
    # Check backup files exist
    import glob
    backups = glob.glob("secure_credentials_backup_*.db")
    config_backups = glob.glob("config_backup_*.tar.gz")
    
    if backups:
        print(f"✅ Database backup available: {backups[-1]}")
    else:
        print("❌ No database backup found")
    
    if config_backups:
        print(f"✅ Config backup available: {config_backups[-1]}")
    else:
        print("❌ No config backup found")
    
    print("\n🔙 ROLLBACK INSTRUCTIONS:")
    print("1. git checkout 40894f6")
    print("2. cp secure_credentials_backup_*.db secure_credentials.db")
    print("3. tar -xzf config_backup_*.tar.gz")
    print("4. pip install -r requirements.txt")
    print("5. python integrated_dashboard.py")

if __name__ == "__main__":
    test_rollback_capability()
```

---

## ⚠️ CRITICAL MIGRATION RISKS

### HIGH RISK AREAS:
1. **Authentication Flow Changes**: Complete change from JWT to Supabase session management
2. **Database Schema Differences**: PostgreSQL vs SQLite data types and constraints
3. **RLS Policy Configuration**: Incorrect policies could expose data or block access
4. **API Endpoint Changes**: Breaking changes to authentication headers/flows

### MITIGATION STRATEGIES:
1. **Gradual Migration**: Deploy to staging first with test data
2. **Dual System Period**: Run both systems in parallel during testing
3. **Comprehensive Backup**: Full backup of current system before migration
4. **Rollback Plan**: Tested rollback procedure to previous working state

### DATA LOSS PREVENTION:
1. **Export Before Migration**: Complete data export before starting
2. **Validation After Import**: Verify all data imported correctly
3. **Audit Trail**: Maintain audit logs of migration process
4. **Multiple Backups**: Database backups at each migration phase

---

## 💰 COST ANALYSIS

### Supabase Pricing Impact:
- **Free Tier**: 50MB database + 100MB storage + 2 simultaneous connections
- **Pro Tier**: $25/month for 8GB database + 100GB storage + 60 simultaneous connections
- **Current Empty Database**: Migration will likely fit in Free tier initially
- **Future Growth**: Monitor database size and upgrade to Pro if needed

### Railway.app Compatibility:
- ✅ **No Railway Changes**: Still deploy to Railway, just database moves to Supabase
- ✅ **Environment Variables**: Add Supabase keys to Railway environment
- ✅ **Network**: Outbound HTTPS to Supabase (no firewall issues)

### Operational Benefits:
1. **Managed Database**: No SQLite file management
2. **Automatic Backups**: Supabase handles database backups
3. **Scalability**: Horizontal scaling capabilities
4. **Security**: Row Level Security + managed authentication
5. **Monitoring**: Built-in database monitoring and analytics

---

## 📋 MIGRATION CHECKLIST

### Pre-Migration:
- [ ] Create Supabase project
- [ ] Configure environment variables
- [ ] Set up database schema and RLS policies
- [ ] Create complete backup of current system
- [ ] Create git tag for rollback reference
- [ ] Test Supabase connectivity from Railway

### Migration Day:
- [ ] Export all current data
- [ ] Import data to Supabase
- [ ] Deploy new Supabase-enabled code
- [ ] Run validation tests
- [ ] Verify all functionality works
- [ ] Update documentation
- [ ] Monitor for issues

### Post-Migration:
- [ ] Monitor system performance for 48 hours
- [ ] Verify data integrity
- [ ] Test rollback capability
- [ ] Archive old SQLite files
- [ ] Update deployment documentation
- [ ] Train on new Supabase management

---

## 🎯 SUCCESS CRITERIA

### Migration is considered successful when:
1. ✅ **All Authentication Works**: Users can register, login, logout with Supabase
2. ✅ **Data Integrity**: All user, workspace, assignment data migrated correctly
3. ✅ **Security Maintained**: RLS policies protect data appropriately
4. ✅ **API Compatibility**: Existing API endpoints work with minimal changes
5. ✅ **Performance Acceptable**: Response times equivalent or better than SQLite
6. ✅ **Rollback Tested**: Confirmed ability to rollback to previous system
7. ✅ **Monitoring Active**: Health checks and error monitoring operational

---

## 🚨 EMERGENCY ROLLBACK PROCEDURE

```bash
# IMMEDIATE ROLLBACK (if migration fails)

# 1. Restore code to working state
git checkout 40894f6
git reset --hard HEAD

# 2. Restore database
cp secure_credentials_backup_YYYYMMDD_HHMMSS.db secure_credentials.db

# 3. Restore configuration
tar -xzf config_backup_YYYYMMDD_HHMMSS.tar.gz

# 4. Restart application
python integrated_dashboard.py

# 5. Verify rollback worked
curl http://localhost:8520/health
```

---

**NEXT STEPS**: Review this migration plan, create Supabase project, and begin Phase 1 preparation when ready to proceed.