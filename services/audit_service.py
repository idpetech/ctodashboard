# Phase 5C: Assignment History/Audit Log Service
import os
import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path


class AuditService:
    """Service to track assignment changes and history"""
    
    def __init__(self):
        self.audit_dir = os.getenv(
            "AUDIT_LOG_PATH",
            "config/audit"
        )
        Path(self.audit_dir).mkdir(exist_ok=True)
    
    def log_assignment_change(self, assignment_id: str, action: str, old_data: Dict = None, new_data: Dict = None, user_email: str = None) -> bool:
        """Log an assignment change event"""
        try:
            audit_entry = {
                "id": f"{assignment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "assignment_id": assignment_id,
                "action": action,  # create, update, delete, archive, resurrect
                "timestamp": datetime.now().isoformat(),
                "user_email": user_email,
                "changes": self._compute_changes(old_data, new_data),
                "old_data": old_data,
                "new_data": new_data
            }
            
            # Write to assignment-specific audit file
            audit_file = Path(self.audit_dir) / f"{assignment_id}.json"
            
            # Load existing audit log
            audit_log = []
            if audit_file.exists():
                try:
                    with open(audit_file, 'r') as f:
                        audit_log = json.load(f)
                except json.JSONDecodeError:
                    audit_log = []
            
            # Add new entry
            audit_log.append(audit_entry)
            
            # Keep only last 100 entries per assignment
            if len(audit_log) > 100:
                audit_log = audit_log[-100:]
            
            # Save updated log
            with open(audit_file, 'w') as f:
                json.dump(audit_log, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error logging audit entry: {e}")
            return False
    
    def get_assignment_history(self, assignment_id: str) -> List[Dict]:
        """Get change history for a specific assignment"""
        try:
            audit_file = Path(self.audit_dir) / f"{assignment_id}.json"
            if not audit_file.exists():
                return []
            
            with open(audit_file, 'r') as f:
                return json.load(f)
        
        except Exception as e:
            print(f"Error retrieving assignment history: {e}")
            return []
    
    def get_recent_changes(self, limit: int = 50) -> List[Dict]:
        """Get recent changes across all assignments"""
        try:
            all_changes = []
            
            for audit_file in Path(self.audit_dir).glob("*.json"):
                with open(audit_file, 'r') as f:
                    audit_log = json.load(f)
                    all_changes.extend(audit_log)
            
            # Sort by timestamp (newest first)
            all_changes.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return all_changes[:limit]
        
        except Exception as e:
            print(f"Error retrieving recent changes: {e}")
            return []
    
    def _compute_changes(self, old_data: Dict = None, new_data: Dict = None) -> List[Dict]:
        """Compute what fields changed between old and new data"""
        if not old_data or not new_data:
            return []
        
        changes = []
        
        # Compare all fields
        all_keys = set(old_data.keys()) | set(new_data.keys())
        
        for key in all_keys:
            old_value = old_data.get(key)
            new_value = new_data.get(key)
            
            if old_value != new_value:
                changes.append({
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        return changes
    
    def delete_assignment_history(self, assignment_id: str) -> bool:
        """Delete all history for an assignment"""
        try:
            audit_file = Path(self.audit_dir) / f"{assignment_id}.json"
            if audit_file.exists():
                audit_file.unlink()
            return True
        except Exception as e:
            print(f"Error deleting assignment history: {e}")
            return False


# Global instance
audit_service = AuditService()