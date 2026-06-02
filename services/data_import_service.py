"""
Data Import Service - Phase 2 Implementation
Augments existing CTO Dashboard functionality with enhanced import capabilities
Compatible with Phase 1 Export Service format
"""

import os
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from services.workspace.workspace_service import WorkspaceService
from services.security.secure_database import SecureDatabaseManager

logger = logging.getLogger(__name__)

class DataImportService:
    """
    Import service that works with both legacy and new export formats.
    Augments existing import functionality with validation and compatibility.
    """
    
    def __init__(self):
        self.workspace_service = WorkspaceService()
        self.secure_db = SecureDatabaseManager()
        
    def validate_import_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate imported data structure and normalize format.
        Handles both legacy and new export formats.
        """
        try:
            validation_result = {
                'valid': True,
                'format_version': 'unknown',
                'normalized_data': data,
                'warnings': [],
                'errors': []
            }
            
            # Check for new format (from our Phase 1 export)
            if 'export_metadata' in data and 'export_version' in data['export_metadata']:
                # New format from our export service
                validation_result['format_version'] = data['export_metadata']['export_version']
                
                # Normalize to legacy format for compatibility
                normalized = {
                    'export_version': data['export_metadata']['export_version'],
                    'workspace_id': data['export_metadata'].get('workspace_id'),
                    'assignments': data.get('assignments', []),
                    'workspace_info': data.get('workspace_info', {}),
                    'metadata': data['export_metadata']
                }
                validation_result['normalized_data'] = normalized
                
            # Check for legacy format
            elif 'export_version' in data:
                validation_result['format_version'] = data['export_version']
                validation_result['normalized_data'] = data
                
            else:
                # Try to handle data without version (legacy)
                if 'assignments' in data:
                    validation_result['warnings'].append('No version info found, assuming legacy format')
                    validation_result['format_version'] = '1.0'
                    validation_result['normalized_data'] = {
                        'export_version': '1.0',
                        'assignments': data.get('assignments', []),
                        'workspace_info': data.get('workspace_info', {}),
                        'metadata': {'legacy_import': True}
                    }
                else:
                    validation_result['valid'] = False
                    validation_result['errors'].append('Invalid import format - no recognizable structure')
                    return validation_result
            
            # Validate version compatibility
            supported_versions = ['1.0']
            if validation_result['format_version'] not in supported_versions:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Unsupported export version: {validation_result['format_version']}. "
                    f"Supported versions: {', '.join(supported_versions)}"
                )
                return validation_result
            
            # Validate assignments structure
            assignments = validation_result['normalized_data'].get('assignments', [])
            for i, assignment in enumerate(assignments):
                if not assignment.get('assignment_id') and not assignment.get('id'):
                    validation_result['errors'].append(f"Assignment {i+1} missing ID field")
                
                # Normalize ID field
                if 'assignment_id' in assignment and 'id' not in assignment:
                    assignment['id'] = assignment['assignment_id']
                elif 'id' in assignment and 'assignment_id' not in assignment:
                    assignment['assignment_id'] = assignment['id']
            
            if validation_result['errors']:
                validation_result['valid'] = False
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                'valid': False,
                'format_version': 'unknown',
                'normalized_data': {},
                'warnings': [],
                'errors': [f"Validation failed: {str(e)}"]
            }
    
    def import_workspace_data(self, workspace_id: str, data: Dict[str, Any], import_mode: str = 'create_new') -> Dict[str, Any]:
        """
        Import workspace data with enhanced validation and conflict resolution.
        Compatible with existing import functionality.
        """
        try:
            # First validate the data
            validation = self.validate_import_data(data)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'warnings': validation['warnings']
                }
            
            normalized_data = validation['normalized_data']
            import_assignments = normalized_data.get('assignments', [])
            
            results = {
                'success': True,
                'imported_assignments': 0,
                'skipped_assignments': 0,
                'updated_assignments': 0,
                'errors': validation['errors'].copy(),
                'warnings': validation['warnings'].copy(),
                'details': [],
                'import_mode': import_mode,
                'format_version': validation['format_version']
            }
            
            # Import workspace info if available
            workspace_info = normalized_data.get('workspace_info', {})
            if workspace_info and import_mode in ['overwrite', 'merge']:
                try:
                    self._import_workspace_info(workspace_id, workspace_info)
                    results['details'].append('Workspace info imported successfully')
                except Exception as e:
                    results['warnings'].append(f'Failed to import workspace info: {str(e)}')
            
            # Import assignments
            for assignment_data in import_assignments:
                assignment_id = assignment_data.get('assignment_id') or assignment_data.get('id')
                if not assignment_id:
                    results['errors'].append("Assignment missing ID - skipped")
                    results['skipped_assignments'] += 1
                    continue
                
                try:
                    import_result = self._import_single_assignment(
                        workspace_id, assignment_id, assignment_data, import_mode
                    )
                    
                    if import_result['success']:
                        if import_result['action'] == 'created':
                            results['imported_assignments'] += 1
                        elif import_result['action'] == 'updated':
                            results['updated_assignments'] += 1
                        results['details'].append(import_result['message'])
                    else:
                        results['errors'].append(import_result['message'])
                        results['skipped_assignments'] += 1
                        
                except Exception as e:
                    error_msg = f"Error importing {assignment_id}: {str(e)}"
                    results['errors'].append(error_msg)
                    results['skipped_assignments'] += 1
                    logger.error(error_msg)
            
            # Update overall success status
            total_processed = results['imported_assignments'] + results['updated_assignments'] + results['skipped_assignments']
            if total_processed == 0:
                results['success'] = len(results['errors']) == 0
            else:
                # Success if more than 50% of assignments were processed successfully
                success_count = results['imported_assignments'] + results['updated_assignments']
                results['success'] = success_count >= (total_processed / 2)
            
            # Log import action
            self._log_import_action(workspace_id, results, normalized_data.get('metadata', {}))
            
            return results
            
        except Exception as e:
            error_msg = f"Import failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'imported_assignments': 0,
                'skipped_assignments': 0,
                'updated_assignments': 0,
                'errors': [error_msg],
                'warnings': [],
                'details': [],
                'import_mode': import_mode
            }
    
    def _import_single_assignment(self, workspace_id: str, assignment_id: str, assignment_data: Dict[str, Any], import_mode: str) -> Dict[str, Any]:
        """Import a single assignment with conflict resolution"""
        try:
            # Check if assignment already exists
            existing = self._get_assignment_from_db(workspace_id, assignment_id)
            
            if existing and import_mode == "create_new":
                # Generate new ID to avoid conflicts
                new_id = f"{assignment_id}_{uuid.uuid4().hex[:8]}"
                assignment_data['assignment_id'] = new_id
                assignment_data['id'] = new_id
                assignment_data['name'] = f"{assignment_data.get('name', assignment_id)} (Imported)"
                assignment_id = new_id
                existing = None
            
            # Prepare assignment data for database
            db_data = {
                'assignment_id': assignment_id,
                'workspace_id': workspace_id,
                'name': assignment_data.get('name', assignment_id),
                'description': assignment_data.get('description', ''),
                'team_size': assignment_data.get('team_size'),
                'monthly_burn_rate': assignment_data.get('monthly_burn_rate'),
                'status': assignment_data.get('status', 'active'),
                'metrics_config': json.dumps(assignment_data.get('metrics_config', {})) if assignment_data.get('metrics_config') else None
            }
            
            if existing:
                if import_mode == "merge":
                    # Merge with existing data, keeping existing values where new ones are None
                    for key, value in db_data.items():
                        if value is None and key in existing:
                            db_data[key] = existing[key]
                
                # Update existing assignment
                success = self._update_assignment_in_db(workspace_id, assignment_id, db_data)
                action = 'updated'
                message = f"Updated assignment: {db_data['name']}"
                
            else:
                # Create new assignment
                success = self._create_assignment_in_db(db_data)
                action = 'created'
                message = f"Created assignment: {db_data['name']}"
            
            return {
                'success': success,
                'action': action,
                'message': message,
                'assignment_id': assignment_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'error',
                'message': f"Failed to import {assignment_id}: {str(e)}",
                'assignment_id': assignment_id
            }
    
    def _create_assignment_in_db(self, assignment_data: Dict[str, Any]) -> bool:
        """Create assignment in secure database"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO secure_assignments 
                (assignment_id, workspace_id, name, description, team_size, monthly_burn_rate, status, metrics_config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment_data['assignment_id'],
                assignment_data['workspace_id'],
                assignment_data['name'],
                assignment_data['description'],
                assignment_data['team_size'],
                assignment_data['monthly_burn_rate'],
                assignment_data['status'],
                assignment_data['metrics_config'],
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create assignment in DB: {str(e)}")
            return False
    
    def _update_assignment_in_db(self, workspace_id: str, assignment_id: str, assignment_data: Dict[str, Any]) -> bool:
        """Update assignment in secure database"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE secure_assignments 
                SET name=?, description=?, team_size=?, monthly_burn_rate=?, status=?, metrics_config=?, updated_at=?
                WHERE workspace_id=? AND assignment_id=?
            """, (
                assignment_data['name'],
                assignment_data['description'],
                assignment_data['team_size'],
                assignment_data['monthly_burn_rate'],
                assignment_data['status'],
                assignment_data['metrics_config'],
                datetime.utcnow(),
                workspace_id,
                assignment_id
            ))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update assignment in DB: {str(e)}")
            return False
    
    def _get_assignment_from_db(self, workspace_id: str, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Get assignment from secure database"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT assignment_id, workspace_id, name, description, team_size, 
                          monthly_burn_rate, status, metrics_config, created_at, updated_at 
                   FROM secure_assignments WHERE workspace_id = ? AND assignment_id = ?""",
                (workspace_id, assignment_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get assignment from DB: {str(e)}")
            return None
    
    def _import_workspace_info(self, workspace_id: str, workspace_info: Dict[str, Any]):
        """Import workspace metadata (if it doesn't exist)"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            
            # Check if workspace exists
            cursor.execute("SELECT workspace_id FROM secure_workspaces WHERE workspace_id = ?", (workspace_id,))
            exists = cursor.fetchone()
            
            if not exists:
                # Create new workspace
                cursor.execute("""
                    INSERT INTO secure_workspaces (workspace_id, name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    workspace_id,
                    workspace_info.get('name', workspace_id),
                    workspace_info.get('description', ''),
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to import workspace info: {str(e)}")
            raise
    
    def _log_import_action(self, workspace_id: str, results: Dict[str, Any], metadata: Dict[str, Any]):
        """Log import action using existing audit system"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            
            # Create audit log entry
            cursor.execute(
                """INSERT INTO credential_audit 
                   (action, entity_type, entity_id, workspace_id, success, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    'import', 
                    'workspace',
                    f"imported_{results.get('imported_assignments', 0)}_assignments",
                    workspace_id, 
                    results['success'], 
                    datetime.utcnow()
                )
            )
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log import action: {str(e)}")
    
    def get_import_templates(self) -> List[Dict[str, Any]]:
        """Get available import templates for quick assignment setup"""
        templates = [
            {
                'id': 'basic_web_app',
                'name': 'Basic Web Application',
                'description': 'Standard web app with frontend, backend, and database',
                'template': {
                    'name': 'New Web Application',
                    'description': 'Basic web application project',
                    'team_size': 3,
                    'monthly_burn_rate': 15000,
                    'status': 'active',
                    'metrics_config': {
                        'github': {'enabled': True},
                        'jira': {'enabled': True}
                    }
                }
            },
            {
                'id': 'mobile_app',
                'name': 'Mobile Application',
                'description': 'Mobile app with backend services',
                'template': {
                    'name': 'New Mobile App',
                    'description': 'Mobile application project',
                    'team_size': 4,
                    'monthly_burn_rate': 20000,
                    'status': 'active',
                    'metrics_config': {
                        'github': {'enabled': True},
                        'jira': {'enabled': True},
                        'aws': {'enabled': True}
                    }
                }
            },
            {
                'id': 'data_pipeline',
                'name': 'Data Pipeline',
                'description': 'Data processing and analytics pipeline',
                'template': {
                    'name': 'New Data Pipeline',
                    'description': 'Data pipeline and analytics project',
                    'team_size': 2,
                    'monthly_burn_rate': 12000,
                    'status': 'active',
                    'metrics_config': {
                        'github': {'enabled': True},
                        'aws': {'enabled': True}
                    }
                }
            }
        ]
        return templates