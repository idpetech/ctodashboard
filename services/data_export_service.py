"""
Data Export Service - Phase 1 Implementation
Augments existing CTO Dashboard functionality with export capabilities
"""

import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List
from services.workspace.workspace_service import WorkspaceService
from services.security.secure_database import secure_db
from config.logging_config import get_logger

logger = get_logger(__name__)

class DataExportService:
    """
    Export service that works with existing CTO Dashboard data structures.
    Augments current functionality without modifying existing code.
    """
    
    def __init__(self):
        self.workspace_service = WorkspaceService()
        self.secure_db = secure_db  # Use singleton instance
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
        
        logger.info("DataExportService initialized with singleton database instance", extra={
            "operation": "service_init",
            "service": "data_export",
            "singleton_used": True
        })
        
    def export_workspace_data(self, workspace_id: str, format: str = 'json', include_assignments: bool = True) -> Dict[str, Any]:
        """
        Export workspace data using existing workspace service.
        Returns export metadata and file path.
        """
        try:
            export_data = {
                'export_metadata': {
                    'workspace_id': workspace_id,
                    'export_format': format,
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'export_version': '1.0',
                    'dashboard_version': self._get_dashboard_version()
                },
                'workspace_info': {},
                'assignments': [],
                'workspace_settings': {}
            }
            
            # Get workspace info from secure database
            workspace_info = self._get_workspace_from_db(workspace_id)
            if workspace_info:
                export_data['workspace_info'] = {
                    'workspace_id': workspace_info.get('workspace_id'),
                    'name': workspace_info.get('name'),
                    'description': workspace_info.get('description'),
                    'created_at': workspace_info.get('created_at'),
                    # Note: settings are excluded for security (may contain sensitive data)
                }
            
            # Get assignments if requested
            if include_assignments:
                assignments = self._get_assignments_for_workspace(workspace_id)
                # Sanitize assignments to include safe connector configs
                sanitized_assignments = []
                for assignment in assignments:
                    sanitized_assignment = assignment.copy()
                    # Add sanitized metrics config
                    sanitized_assignment['metrics_config'] = self._sanitize_metrics_config(
                        assignment.get('metrics_config')
                    )
                    sanitized_assignments.append(sanitized_assignment)
                export_data['assignments'] = sanitized_assignments
            
            # Generate filename and save
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"workspace_{workspace_id}_{timestamp}.{format}"
            file_path = self.export_dir / filename
            
            if format.lower() == 'json':
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            elif format.lower() == 'csv':
                self._export_to_csv(export_data, file_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            # Log export action (augmenting existing audit capabilities)
            self._log_export_action(workspace_id, 'workspace', format, str(file_path))
            
            return {
                'success': True,
                'file_path': str(file_path),
                'filename': filename,
                'format': format,
                'size_bytes': file_path.stat().st_size,
                'records_exported': len(export_data.get('assignments', [])),
                'export_timestamp': export_data['export_metadata']['export_timestamp']
            }
            
        except Exception as e:
            logger.error(f"Export failed for workspace {workspace_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def export_assignment_data(self, workspace_id: str, assignment_id: str, format: str = 'json') -> Dict[str, Any]:
        """
        Export single assignment data with all metrics and configurations.
        Uses existing assignment structure without modifications.
        """
        try:
            # Get assignment from existing structure
            assignment = self._get_assignment_from_db(workspace_id, assignment_id)
            if not assignment:
                raise ValueError(f"Assignment {assignment_id} not found in workspace {workspace_id}")
            
            export_data = {
                'export_metadata': {
                    'workspace_id': workspace_id,
                    'assignment_id': assignment_id,
                    'export_format': format,
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'export_version': '1.0'
                },
                'assignment': {
                    'assignment_id': assignment.get('assignment_id'),
                    'name': assignment.get('name'),
                    'description': assignment.get('description'),
                    'team_size': assignment.get('team_size'),
                    'monthly_burn_rate': assignment.get('monthly_burn_rate'),
                    'status': assignment.get('status'),
                    'created_at': assignment.get('created_at'),
                    'updated_at': assignment.get('updated_at'),
                    'metrics_config': self._sanitize_metrics_config(assignment.get('metrics_config'))
                },
                'connector_types': self._get_connector_types_for_assignment(workspace_id, assignment_id)
            }
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"assignment_{assignment_id}_{timestamp}.{format}"
            file_path = self.export_dir / filename
            
            if format.lower() == 'json':
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            elif format.lower() == 'csv':
                self._export_assignment_to_csv(export_data, file_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self._log_export_action(workspace_id, 'assignment', format, str(file_path))
            
            return {
                'success': True,
                'file_path': str(file_path),
                'filename': filename,
                'format': format,
                'size_bytes': file_path.stat().st_size,
                'export_timestamp': export_data['export_metadata']['export_timestamp']
            }
            
        except Exception as e:
            logger.error(f"Assignment export failed for {assignment_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def list_exports(self, workspace_id: str = None) -> List[Dict[str, Any]]:
        """List available export files, optionally filtered by workspace"""
        try:
            exports = []
            for export_file in self.export_dir.glob("*"):
                if export_file.is_file():
                    # Parse filename to extract metadata
                    file_info = self._parse_export_filename(export_file.name)
                    if workspace_id and file_info.get('workspace_id') != workspace_id:
                        continue
                        
                    stat = export_file.stat()
                    exports.append({
                        'filename': export_file.name,
                        'file_path': str(export_file),
                        'size_bytes': stat.st_size,
                        'size_human': self._format_file_size(stat.st_size),
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        **file_info
                    })
            
            # Sort by creation time, newest first
            exports.sort(key=lambda x: x['created_at'], reverse=True)
            return exports
            
        except Exception as e:
            logger.error(f"Failed to list exports: {str(e)}")
            return []
    
    def _get_workspace_from_db(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace data from secure database using existing connection"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT workspace_id, name, description, created_at, updated_at FROM secure_workspaces WHERE workspace_id = ?",
                (workspace_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get workspace {workspace_id}: {str(e)}")
            return None
    
    def _get_assignments_for_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get assignments for workspace from file system (dashboard uses file-based storage)"""
        try:
            assignments = []
            workspace_assignments_dir = Path(f"config/workspaces/{workspace_id}/assignments")
            
            if workspace_assignments_dir.exists():
                for assignment_file in workspace_assignments_dir.glob("*.json"):
                    try:
                        with open(assignment_file, 'r') as f:
                            assignment_data = json.load(f)
                        assignments.append(assignment_data)
                    except Exception as e:
                        logger.warning(f"Failed to read assignment file {assignment_file}: {str(e)}")
                        continue
            
            return assignments
        except Exception as e:
            logger.error(f"Failed to get assignments for workspace {workspace_id}: {str(e)}")
            return []
    
    def _get_assignment_from_db(self, workspace_id: str, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Get single assignment from file system (dashboard uses file-based storage)"""
        try:
            assignment_file = Path(f"config/workspaces/{workspace_id}/assignments/{assignment_id}.json")
            
            if assignment_file.exists():
                with open(assignment_file, 'r') as f:
                    assignment_data = json.load(f)
                return assignment_data
            else:
                logger.warning(f"Assignment file not found: {assignment_file}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get assignment {assignment_id}: {str(e)}")
            return None
    
    def _get_connector_types_for_assignment(self, workspace_id: str, assignment_id: str) -> List[str]:
        """Get connector types configured for an assignment (without credentials)"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT connector_type FROM secure_credentials WHERE workspace_id = ? AND assignment_id = ?",
                (workspace_id, assignment_id)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get connector types: {str(e)}")
            return []
    
    def _export_to_csv(self, export_data: Dict[str, Any], file_path: Path):
        """Export workspace data to CSV format"""
        with open(file_path, 'w', newline='') as csvfile:
            if export_data.get('assignments'):
                fieldnames = ['assignment_id', 'name', 'description', 'team_size', 'monthly_burn_rate', 'status', 'created_at', 'updated_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for assignment in export_data['assignments']:
                    writer.writerow({k: assignment.get(k) for k in fieldnames})
            else:
                # Empty workspace
                writer = csv.writer(csvfile)
                writer.writerow(['workspace_id', 'export_timestamp'])
                writer.writerow([export_data['export_metadata']['workspace_id'], export_data['export_metadata']['export_timestamp']])
    
    def _export_assignment_to_csv(self, export_data: Dict[str, Any], file_path: Path):
        """Export assignment data to CSV format"""
        with open(file_path, 'w', newline='') as csvfile:
            assignment = export_data['assignment']
            writer = csv.writer(csvfile)
            writer.writerow(['Field', 'Value'])
            for key, value in assignment.items():
                writer.writerow([key, value])
    
    def _log_export_action(self, workspace_id: str, export_type: str, format: str, file_path: str):
        """Log export action using existing audit system"""
        try:
            conn = self.secure_db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO credential_audit 
                   (action, entity_type, entity_id, workspace_id, success, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ('export', export_type, file_path, workspace_id, True, datetime.utcnow())
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log export action: {str(e)}")
    
    def _get_dashboard_version(self) -> str:
        """Get dashboard version for export metadata"""
        try:
            # Try to get from package.json or other version file
            return "1.0"  # Fallback version
        except:
            return "unknown"
    
    def _parse_export_filename(self, filename: str) -> Dict[str, Any]:
        """Parse export filename to extract metadata"""
        try:
            # Expected format: workspace_WORKSPACEID_TIMESTAMP.format or assignment_ASSIGNMENTID_TIMESTAMP.format
            name_without_ext = filename.rsplit('.', 1)[0]
            parts = name_without_ext.split('_')
            
            if len(parts) >= 3:
                export_type = parts[0]  # 'workspace' or 'assignment'
                entity_id = parts[1]
                timestamp = parts[2]
                
                return {
                    'export_type': export_type,
                    'workspace_id' if export_type == 'workspace' else 'assignment_id': entity_id,
                    'timestamp': timestamp,
                    'format': filename.split('.')[-1] if '.' in filename else 'unknown'
                }
        except:
            pass
        
        return {'export_type': 'unknown', 'format': 'unknown'}
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _sanitize_metrics_config(self, metrics_config) -> Dict[str, Any]:
        """
        Safely export metrics config without credentials.
        Includes connector configuration but removes sensitive data.
        """
        try:
            if not metrics_config:
                return {}
            
            # Parse JSON if it's a string, otherwise use as-is
            if isinstance(metrics_config, str):
                try:
                    config = json.loads(metrics_config)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse metrics_config as JSON")
                    return {}
            else:
                config = metrics_config
            
            # Sanitize each connector config
            sanitized_config = {}
            
            for connector_type, connector_config in config.items():
                if isinstance(connector_config, dict):
                    # Start with a copy of the config
                    safe_config = connector_config.copy()
                    
                    # Remove the entire auth_instance section (contains credentials)
                    if 'auth_instance' in safe_config:
                        del safe_config['auth_instance']
                    
                    # Remove any field that might contain credentials
                    unsafe_fields = [
                        'token', 'key', 'secret', 'password', 'credential', 
                        'auth', 'api_key', 'access_key', 'private_key',
                        'client_secret', 'webhook_secret', 'credentials'
                    ]
                    
                    # Remove unsafe fields at any level
                    keys_to_remove = []
                    for field in safe_config.keys():
                        if any(unsafe_word in field.lower() for unsafe_word in unsafe_fields):
                            keys_to_remove.append(field)
                    
                    for key in keys_to_remove:
                        del safe_config[key]
                    
                    # Only include if there's meaningful config data
                    if safe_config:
                        sanitized_config[connector_type] = safe_config
            
            return sanitized_config
            
        except Exception as e:
            logger.warning(f"Failed to sanitize metrics config: {str(e)}")
            return {"error": "Config sanitization failed"}