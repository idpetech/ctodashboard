#!/usr/bin/env python3
"""
Phase 5C: Backup/Restore Commands for CTO Dashboard
CLI tool for backing up and restoring all dashboard data
"""

import os
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
import zipfile
import tempfile


class BackupManager:
    """Manager for backup and restore operations"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.config_dir = self.base_dir / "config"
        self.services_dir = self.base_dir / "services"
        self.backup_dir = self.base_dir / "backups"
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, backup_name=None, include_audit=True, include_services=False):
        """Create a full backup of all dashboard data"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"ctodash_backup_{timestamp}"
        
        backup_file = self.backup_dir / f"{backup_name}.zip"
        
        print(f"🔄 Creating backup: {backup_name}")
        print(f"📁 Backup file: {backup_file}")
        
        try:
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                
                # Backup configuration files
                if self.config_dir.exists():
                    print("📋 Backing up configurations...")
                    for file_path in self.config_dir.rglob("*.json"):
                        arcname = file_path.relative_to(self.base_dir)
                        zip_file.write(file_path, arcname)
                        print(f"   ✓ {arcname}")
                
                # Backup audit logs if requested
                if include_audit:
                    audit_dir = self.config_dir / "audit"
                    if audit_dir.exists():
                        print("📜 Backing up audit logs...")
                        for file_path in audit_dir.rglob("*.json"):
                            arcname = file_path.relative_to(self.base_dir)
                            zip_file.write(file_path, arcname)
                            print(f"   ✓ {arcname}")
                
                # Backup service files if requested
                if include_services:
                    if self.services_dir.exists():
                        print("⚙️ Backing up service configurations...")
                        for file_path in self.services_dir.rglob("*.py"):
                            if not file_path.name.startswith("__"):
                                arcname = file_path.relative_to(self.base_dir)
                                zip_file.write(file_path, arcname)
                                print(f"   ✓ {arcname}")
                
                # Create backup metadata
                metadata = {
                    "backup_name": backup_name,
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "includes": {
                        "configurations": True,
                        "audit_logs": include_audit,
                        "service_files": include_services
                    },
                    "source_directory": str(self.base_dir)
                }
                
                # Add metadata to zip
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as meta_file:
                    json.dump(metadata, meta_file, indent=2)
                    meta_path = Path(meta_file.name)
                
                zip_file.write(meta_path, "backup_metadata.json")
                meta_path.unlink()  # Clean up temp file
            
            print(f"✅ Backup created successfully: {backup_file}")
            print(f"📊 Backup size: {backup_file.stat().st_size / 1024:.1f} KB")
            return str(backup_file)
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            if backup_file.exists():
                backup_file.unlink()
            return None
    
    def list_backups(self):
        """List all available backups"""
        backups = list(self.backup_dir.glob("*.zip"))
        
        if not backups:
            print("📭 No backups found")
            return []
        
        print(f"📋 Found {len(backups)} backup(s):")
        backup_info = []
        
        for backup_file in sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                # Try to read metadata
                with zipfile.ZipFile(backup_file, 'r') as zip_file:
                    if "backup_metadata.json" in zip_file.namelist():
                        with zip_file.open("backup_metadata.json") as meta_file:
                            metadata = json.load(meta_file)
                            created_at = metadata.get("created_at", "Unknown")
                            includes = metadata.get("includes", {})
                    else:
                        # Fallback for backups without metadata
                        created_at = datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                        includes = {"configurations": True, "audit_logs": True, "service_files": False}
                
                size_kb = backup_file.stat().st_size / 1024
                
                info = {
                    "file": backup_file.name,
                    "path": str(backup_file),
                    "created_at": created_at,
                    "size_kb": size_kb,
                    "includes": includes
                }
                backup_info.append(info)
                
                print(f"   📦 {backup_file.name}")
                print(f"      Created: {created_at}")
                print(f"      Size: {size_kb:.1f} KB")
                print(f"      Includes: {', '.join([k for k, v in includes.items() if v])}")
                print()
                
            except Exception as e:
                print(f"   ⚠️ {backup_file.name} (corrupted: {e})")
        
        return backup_info
    
    def restore_backup(self, backup_file, target_dir=None, dry_run=False):
        """Restore from a backup file"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            # Try looking in backup directory
            backup_path = self.backup_dir / backup_file
            if not backup_path.exists():
                print(f"❌ Backup file not found: {backup_file}")
                return False
        
        if not target_dir:
            target_dir = self.base_dir
        else:
            target_dir = Path(target_dir)
        
        print(f"🔄 {'[DRY RUN] ' if dry_run else ''}Restoring backup: {backup_path.name}")
        print(f"📁 Target directory: {target_dir}")
        
        if dry_run:
            print("🔍 This is a dry run - no files will be changed")
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zip_file:
                
                # Read metadata if available
                metadata = {}
                if "backup_metadata.json" in zip_file.namelist():
                    with zip_file.open("backup_metadata.json") as meta_file:
                        metadata = json.load(meta_file)
                        print(f"📋 Backup created: {metadata.get('created_at', 'Unknown')}")
                        print(f"📋 Backup version: {metadata.get('version', 'Unknown')}")
                
                # Create target directory if it doesn't exist
                if not dry_run:
                    target_dir.mkdir(parents=True, exist_ok=True)
                
                # Extract all files
                file_count = 0
                for file_info in zip_file.filelist:
                    if file_info.filename == "backup_metadata.json":
                        continue  # Skip metadata file
                    
                    target_path = target_dir / file_info.filename
                    
                    if dry_run:
                        print(f"   📄 Would restore: {file_info.filename}")
                    else:
                        # Create directory if needed
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Extract file
                        with zip_file.open(file_info.filename) as source:
                            with open(target_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                        
                        print(f"   ✓ Restored: {file_info.filename}")
                    
                    file_count += 1
                
                if dry_run:
                    print(f"🔍 Dry run complete - {file_count} files would be restored")
                else:
                    print(f"✅ Restore completed successfully - {file_count} files restored")
                
                return True
                
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def delete_backup(self, backup_file):
        """Delete a backup file"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            backup_path = self.backup_dir / backup_file
        
        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_file}")
            return False
        
        try:
            backup_path.unlink()
            print(f"✅ Backup deleted: {backup_path.name}")
            return True
        except Exception as e:
            print(f"❌ Failed to delete backup: {e}")
            return False


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="CTO Dashboard Backup/Restore Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create a new backup')
    backup_parser.add_argument('--name', help='Custom backup name')
    backup_parser.add_argument('--no-audit', action='store_true', help='Exclude audit logs')
    backup_parser.add_argument('--include-services', action='store_true', help='Include service files')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all backups')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_file', help='Backup file name or path')
    restore_parser.add_argument('--target', help='Target directory for restore')
    restore_parser.add_argument('--dry-run', action='store_true', help='Show what would be restored without doing it')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a backup')
    delete_parser.add_argument('backup_file', help='Backup file name or path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    backup_manager = BackupManager()
    
    if args.command == 'backup':
        result = backup_manager.create_backup(
            backup_name=args.name,
            include_audit=not args.no_audit,
            include_services=args.include_services
        )
        if result:
            print(f"\n💡 To restore this backup later, run:")
            print(f"   python backup_restore.py restore {Path(result).name}")
    
    elif args.command == 'list':
        backup_manager.list_backups()
    
    elif args.command == 'restore':
        success = backup_manager.restore_backup(
            backup_file=args.backup_file,
            target_dir=args.target,
            dry_run=args.dry_run
        )
        if success and not args.dry_run:
            print(f"\n💡 Restart the dashboard application to use restored data")
    
    elif args.command == 'delete':
        backup_manager.delete_backup(args.backup_file)


if __name__ == "__main__":
    main()