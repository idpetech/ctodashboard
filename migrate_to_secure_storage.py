#!/usr/bin/env python3
"""
🔒 Security Migration Script
Migrates from plain-text file storage to encrypted SQLite database storage

CRITICAL: This script addresses the security vulnerability of storing credentials
in plain text files that are committed to git repository.

Usage:
    python migrate_to_secure_storage.py [--dry-run] [--force]
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

# Configure logging for migration script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.security.secure_database import secure_db


class SecurityMigrationTool:
    """
    Tool for migrating from insecure file storage to encrypted database storage
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.migration_report = {
            "users_migrated": 0,
            "assignments_migrated": 0,
            "credentials_migrated": 0,
            "files_cleaned": 0,
            "errors": [],
            "warnings": []
        }
    
    def run_migration(self, force: bool = False) -> Dict[str, Any]:
        """
        Run complete security migration
        """
        logger.info("🔒 CTO Dashboard Security Migration")
        logger.info("===================================")
        
        if not force:
            logger.warning("This migration will:")
            logger.warning("   • Move all credentials to encrypted SQLite database")
            logger.warning("   • Remove plain-text credentials from JSON files")
            logger.warning("   • Clean git-tracked files of sensitive data")
            logger.warning("   • Add secure database file to .gitignore")
            
            if not self.dry_run:
                confirm = input("\nContinue with migration? [y/N]: ")
                if confirm.lower() != 'y':
                    logger.info("Migration cancelled.")
                    return {"cancelled": True}
        
        logger.info("🚀 Starting migration %s", '(DRY RUN)' if self.dry_run else '(LIVE)')
        
        # Step 1: Migrate users
        self._migrate_users()
        
        # Step 2: Migrate workspaces and assignments
        self._migrate_workspaces_and_assignments()
        
        # Step 3: Clean files and secure repository
        self._clean_and_secure_files()
        
        # Step 4: Verify migration
        self._verify_migration()
        
        # Step 5: Generate report
        return self._generate_report()
    
    def _migrate_users(self):
        """Migrate user data from JSON files to secure database"""
        logger.info("📁 Migrating user data...")
        
        users_dir = Path("config/users")
        if not users_dir.exists():
            logger.info("   No users directory found - skipping")
            return
        
        for user_file in users_dir.glob("*.json"):
            if user_file.name == "README.md":
                continue
            
            try:
                with open(user_file, 'r') as f:
                    user_data = json.load(f)
                
                email = user_data.get("email")
                if not email:
                    self.migration_report["warnings"].append(f"No email in {user_file.name}")
                    continue
                
                logger.info("   Migrating user: %s", email)
                
                if not self.dry_run:
                    audit_info = {
                        "user_email": "migration_script",
                        "ip_address": "127.0.0.1",
                        "user_agent": "migration_script"
                    }
                    
                    if secure_db.store_user_credentials(email, user_data, audit_info):
                        self.migration_report["users_migrated"] += 1
                    else:
                        self.migration_report["errors"].append(f"Failed to migrate user {email}")
                else:
                    self.migration_report["users_migrated"] += 1
                    logger.info("   [DRY RUN] Would migrate user: %s", email)
            
            except Exception as e:
                error_msg = f"Error migrating user {user_file.name}: {str(e)}"
                self.migration_report["errors"].append(error_msg)
                logger.error("   ❌ %s", error_msg)
    
    def _migrate_workspaces_and_assignments(self):
        """Migrate workspace and assignment data"""
        logger.info("🏢 Migrating workspaces and assignments...")
        
        workspaces_dir = Path("config/workspaces")
        if not workspaces_dir.exists():
            logger.info("   No workspaces directory found - skipping")
            return
        
        for item in workspaces_dir.iterdir():
            if item.is_file() and item.suffix == ".json":
                # Workspace metadata file
                continue
            elif item.is_dir():
                self._migrate_workspace(item)
    
    def _migrate_workspace(self, workspace_dir: Path):
        """Migrate a single workspace"""
        workspace_id = workspace_dir.name
        logger.info("   Migrating workspace: %s", workspace_id)
        
        assignments_dir = workspace_dir / "assignments"
        if assignments_dir.exists():
            for assignment_file in assignments_dir.glob("*.json"):
                self._migrate_assignment(workspace_id, assignment_file)
    
    def _migrate_assignment(self, workspace_id: str, assignment_file: Path):
        """Migrate a single assignment"""
        try:
            with open(assignment_file, 'r') as f:
                assignment_data = json.load(f)
            
            assignment_id = assignment_data.get("id")
            if not assignment_id:
                self.migration_report["warnings"].append(f"No ID in {assignment_file.name}")
                return
            
            logger.info("     Assignment: %s", assignment_id)
            
            # Store assignment metadata (without credentials)
            if not self.dry_run:
                if secure_db.store_assignment(assignment_data):
                    self.migration_report["assignments_migrated"] += 1
            else:
                self.migration_report["assignments_migrated"] += 1
            
            # Migrate credentials
            metrics_config = assignment_data.get("metrics_config", {})
            for connector_type, config in metrics_config.items():
                auth_instance = config.get("auth_instance", {})
                credentials = auth_instance.get("credentials", {})
                
                # Check if there are actual credentials (not empty strings)
                if credentials and any(v for v in credentials.values() if v):
                    logger.info("       🔑 Migrating %s credentials", connector_type)
                    
                    if not self.dry_run:
                        audit_info = {
                            "user_email": "migration_script",
                            "workspace_id": workspace_id,
                            "connector_type": connector_type
                        }
                        
                        if secure_db.store_assignment_credentials(workspace_id, assignment_id, connector_type, credentials, audit_info):
                            self.migration_report["credentials_migrated"] += 1
                        else:
                            self.migration_report["errors"].append(f"Failed to migrate {connector_type} credentials for {assignment_id}")
                    else:
                        self.migration_report["credentials_migrated"] += 1
                        logger.info("       [DRY RUN] Would migrate %s credentials", connector_type)
        
        except Exception as e:
            error_msg = f"Error migrating assignment {assignment_file.name}: {str(e)}"
            self.migration_report["errors"].append(error_msg)
            logger.error("     ❌ %s", error_msg)
    
    def _clean_and_secure_files(self):
        """Clean credential data from files and secure repository"""
        logger.info("🧹 Cleaning credential data from files...")
        
        if self.dry_run:
            logger.info("   [DRY RUN] Would clean all credential data from JSON files")
            logger.info("   [DRY RUN] Would update .gitignore to exclude sensitive files")
            logger.info("   [DRY RUN] Would add database file to .gitignore")
            return
        
        # Clean user files
        self._clean_user_files()
        
        # Clean assignment files
        self._clean_assignment_files()
        
        # Update .gitignore
        self._update_gitignore()
    
    def _clean_user_files(self):
        """Remove sensitive data from user JSON files"""
        users_dir = Path("config/users")
        if not users_dir.exists():
            return
        
        for user_file in users_dir.glob("*.json"):
            if user_file.name == "README.md":
                continue
            
            try:
                with open(user_file, 'r') as f:
                    user_data = json.load(f)
                
                # Remove sensitive fields
                cleaned_data = {
                    "email": user_data.get("email"),
                    "display_name": user_data.get("display_name"),
                    "workspaces": user_data.get("workspaces", []),
                    "role": user_data.get("role"),
                    "status": user_data.get("status"),
                    "preferences": user_data.get("preferences", {}),
                    "created_at": user_data.get("created_at"),
                    "last_login": user_data.get("last_login")
                }
                
                # Write cleaned data back
                with open(user_file, 'w') as f:
                    json.dump(cleaned_data, f, indent=2)
                
                self.migration_report["files_cleaned"] += 1
                logger.info("   Cleaned: %s", user_file.name)
            
            except Exception as e:
                error_msg = f"Error cleaning user file {user_file.name}: {str(e)}"
                self.migration_report["errors"].append(error_msg)
                logger.error("   ❌ %s", error_msg)
    
    def _clean_assignment_files(self):
        """Remove credential data from assignment JSON files"""
        workspaces_dir = Path("config/workspaces")
        if not workspaces_dir.exists():
            return
        
        for workspace_dir in workspaces_dir.iterdir():
            if workspace_dir.is_dir():
                assignments_dir = workspace_dir / "assignments"
                if assignments_dir.exists():
                    for assignment_file in assignments_dir.glob("*.json"):
                        self._clean_assignment_file(assignment_file)
    
    def _clean_assignment_file(self, assignment_file: Path):
        """Clean a single assignment file"""
        try:
            with open(assignment_file, 'r') as f:
                assignment_data = json.load(f)
            
            # Clean credentials from metrics_config
            metrics_config = assignment_data.get("metrics_config", {})
            for connector_type, config in metrics_config.items():
                if "auth_instance" in config:
                    # Keep auth status but remove credentials
                    auth_instance = config["auth_instance"]
                    auth_instance["credentials"] = {}  # Empty credentials
                    # Keep other metadata like auth_configured, last_updated
            
            # Write cleaned data back
            with open(assignment_file, 'w') as f:
                json.dump(assignment_data, f, indent=2)
            
            self.migration_report["files_cleaned"] += 1
            logger.info("   Cleaned: %s", assignment_file.name)
        
        except Exception as e:
            error_msg = f"Error cleaning assignment file {assignment_file.name}: {str(e)}"
            self.migration_report["errors"].append(error_msg)
            logger.error("   ❌ %s", error_msg)
    
    def _update_gitignore(self):
        """Update .gitignore to exclude secure database"""
        gitignore_path = Path(".gitignore")
        
        secure_entries = [
            "# 🔒 SECURE: Never commit encrypted database",
            "config/secure_credentials.db",
            "config/secure_credentials.db-wal",
            "config/secure_credentials.db-shm"
        ]
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                content = f.read()
            
            # Add entries if not already present
            for entry in secure_entries:
                if entry not in content:
                    content += f"\n{entry}"
            
            with open(gitignore_path, 'w') as f:
                f.write(content)
            
            logger.info("   Updated .gitignore with secure database exclusions")
    
    def _verify_migration(self):
        """Verify migration was successful"""
        logger.info("✅ Verifying migration...")
        
        if self.dry_run:
            logger.info("   [DRY RUN] Would verify database connectivity and data integrity")
            return
        
        # Test database health
        health = secure_db.health_check()
        if health["database_connected"]:
            logger.info("   ✅ Database connected successfully")
            logger.info("   📊 Users: %s", health['statistics']['users'])
            logger.info("   📊 Assignments: %s", health['statistics']['assignments'])
            logger.info("   📊 Credentials: %s", health['statistics']['credentials'])
        else:
            error_msg = f"Database connection failed: {health.get('error')}"
            self.migration_report["errors"].append(error_msg)
            logger.error("   ❌ %s", error_msg)
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate migration report"""
        logger.info("📋 Migration Report")
        logger.info("==================")
        logger.info("Users migrated: %s", self.migration_report['users_migrated'])
        logger.info(f"Assignments migrated: {self.migration_report['assignments_migrated']}")
        logger.info(f"Credentials migrated: {self.migration_report['credentials_migrated']}")
        logger.info(f"Files cleaned: {self.migration_report['files_cleaned']}")
        
        if self.migration_report["warnings"]:
            logger.warning("Warnings (%s):", len(self.migration_report['warnings']))
            for warning in self.migration_report["warnings"]:
                logger.info(f"   • {warning}")
        
        if self.migration_report["errors"]:
            logger.info(f"\n❌ Errors ({len(self.migration_report['errors'])}):")
            for error in self.migration_report["errors"]:
                logger.info(f"   • {error}")
        else:
            logger.info("\n🎉 Migration completed successfully!")
            
            if not self.dry_run:
                logger.info("\n🔒 SECURITY IMPROVEMENTS:")
                logger.info("   ✅ All credentials now encrypted with AES")
                logger.info("   ✅ Master key required via environment variable")
                logger.info("   ✅ Database transactions ensure data integrity")
                logger.info("   ✅ Audit logging for all credential access")
                logger.info("   ✅ No more plain-text credentials in git repository")
                logger.info("\n🚨 IMPORTANT: Set CREDENTIAL_MASTER_KEY environment variable for production!")
        
        return self.migration_report


def main():
    parser = argparse.ArgumentParser(description="Migrate to secure credential storage")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    # Check if cryptography is available
    try:
        import cryptography
    except ImportError:
        logger.info("❌ Error: cryptography library not installed")
        logger.info("   Run: pip install cryptography>=3.4.8")
        sys.exit(1)
    
    migration_tool = SecurityMigrationTool(dry_run=args.dry_run)
    report = migration_tool.run_migration(force=args.force)
    
    if report.get("cancelled"):
        sys.exit(1)
    
    # Exit with error code if there were errors
    if report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()