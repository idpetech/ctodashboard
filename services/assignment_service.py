# Assignment service - handles loading configs from JSON (for now) and DB (later)
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class AssignmentService:
    """Service to manage assignment configurations"""
    
    def __init__(self):
        # Get assignments directory from environment variable (never hardcode!)
        self.assignments_dir = os.getenv(
            "ASSIGNMENTS_CONFIG_PATH", 
            os.path.join(os.path.dirname(__file__), "assignments")
        )
        self.archived_dir = os.path.join(self.assignments_dir, "archived")
        
        # Ensure directories exist
        Path(self.assignments_dir).mkdir(exist_ok=True)
        Path(self.archived_dir).mkdir(exist_ok=True)
    
    def get_all_assignments(self, include_archived: bool = False) -> List[Dict]:
        """Get all assignment configurations"""
        assignments = []
        
        # Get active assignments
        for json_file in Path(self.assignments_dir).glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    assignment = json.load(f)
                    assignments.append(assignment)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading {json_file}: {e}")
        
        # Get archived assignments if requested
        if include_archived:
            for json_file in Path(self.archived_dir).glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        assignment = json.load(f)
                        assignment["status"] = "archived"
                        assignments.append(assignment)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Error loading archived {json_file}: {e}")
        
        return assignments
    
    def get_assignment(self, assignment_id: str) -> Optional[Dict]:
        """Get a specific assignment configuration"""
        # Try active assignments first
        json_path = Path(self.assignments_dir) / f"{assignment_id}.json"
        if json_path.exists():
            try:
                with open(json_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading {json_path}: {e}")
                return None
        
        # Try archived assignments
        archived_path = Path(self.archived_dir) / f"{assignment_id}.json"
        if archived_path.exists():
            try:
                with open(archived_path, 'r') as f:
                    assignment = json.load(f)
                    assignment["status"] = "archived"
                    return assignment
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading archived {archived_path}: {e}")
                return None
        
        return None
    
    def create_assignment(self, assignment_data: Dict) -> bool:
        """Create a new assignment configuration"""
        try:
            assignment_id = assignment_data.get("id")
            if not assignment_id:
                return False
            
            json_path = Path(self.assignments_dir) / f"{assignment_id}.json"
            with open(json_path, 'w') as f:
                json.dump(assignment_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error creating assignment: {e}")
            return False
    
    def update_assignment(self, assignment_id: str, assignment_data: Dict) -> bool:
        """Update an existing assignment configuration"""
        try:
            json_path = Path(self.assignments_dir) / f"{assignment_id}.json"
            if not json_path.exists():
                return False
            
            with open(json_path, 'w') as f:
                json.dump(assignment_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error updating assignment: {e}")
            return False
    
    def archive_assignment(self, assignment_id: str) -> bool:
        """Move assignment to archived folder"""
        try:
            active_path = Path(self.assignments_dir) / f"{assignment_id}.json"
            archived_path = Path(self.archived_dir) / f"{assignment_id}.json"
            
            if not active_path.exists():
                return False
            
            # Move file to archived folder
            active_path.rename(archived_path)
            
            # Update status in archived file
            with open(archived_path, 'r') as f:
                assignment = json.load(f)
            
            assignment["status"] = "archived"
            assignment["archived_date"] = datetime.now().isoformat()
            
            with open(archived_path, 'w') as f:
                json.dump(assignment, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error archiving assignment: {e}")
            return False
    
    def resurrect_assignment(self, assignment_id: str) -> bool:
        """Move assignment from archived back to active"""
        try:
            archived_path = Path(self.archived_dir) / f"{assignment_id}.json"
            active_path = Path(self.assignments_dir) / f"{assignment_id}.json"
            
            if not archived_path.exists():
                return False
            
            # Move file back to active folder
            archived_path.rename(active_path)
            
            # Update status in active file
            with open(active_path, 'r') as f:
                assignment = json.load(f)
            
            assignment["status"] = "active"
            if "archived_date" in assignment:
                del assignment["archived_date"]
            
            with open(active_path, 'w') as f:
                json.dump(assignment, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error resurrecting assignment: {e}")
            return False


# TODO: Database migration service for later
class DatabaseMigrationService:
    """Service to migrate from JSON to SQLite database"""
    
    def migrate_json_to_db(self):
        """Migrate existing JSON configs to database"""
        # This will be implemented when we move to database storage
        pass