"""
Connector Registry - Plugin architecture for API connectors

Provides a centralized registry for all connectors with factory methods
for creating connector instances. This enables clean separation and
easy addition of new connectors without modifying existing code.
"""

import logging
from typing import Dict, Type, Optional, Any

from .base.base_connector import BaseConnector
from .base.exceptions import UnknownConnectorError

logger = logging.getLogger(__name__)

class ConnectorRegistry:
    """
    Registry for managing all available API connectors
    
    Provides factory methods for creating connector instances and
    managing connector metadata.
    """
    
    # Connector class registry
    _connectors: Dict[str, Type[BaseConnector]] = {}
    
    # Lazy loading to avoid circular imports
    _loaded = False
    
    @classmethod
    def _load_connectors(cls):
        """Lazy load connector classes to avoid import issues"""
        if cls._loaded:
            return
            
        try:
            # Import available connector classes
            connectors = {}
            
            # OpenAI connector (available)
            try:
                from .openai.connector import OpenAIConnector
                connectors["openai"] = OpenAIConnector
            except ImportError as e:
                logger.warning(f"OpenAI connector not available: {e}")
            
            # Future connectors (will add as we extract them)
            # from .github.connector import GitHubConnector  
            # from .aws.connector import AWSConnector        
            # from .jira.connector import JiraConnector      
            
            cls._connectors = connectors
            cls._loaded = True
            logger.info(f"Loaded {len(cls._connectors)} connectors: {list(cls._connectors.keys())}")
            
        except Exception as e:
            logger.warning(f"Error loading connectors: {e}")
            # Still mark as loaded to avoid retry loops
            cls._loaded = True
    
    @classmethod
    def get_connector(cls, connector_type: str, workspace_id: Optional[str] = None, 
                     assignment_id: Optional[str] = None) -> BaseConnector:
        """
        Create a connector instance
        
        Args:
            connector_type: Type of connector (github, aws, openai, jira)
            workspace_id: Optional workspace context
            assignment_id: Optional assignment context
            
        Returns:
            Configured connector instance
            
        Raises:
            UnknownConnectorError: If connector type is not registered
        """
        cls._load_connectors()
        
        connector_class = cls._connectors.get(connector_type)
        if not connector_class:
            available = list(cls._connectors.keys())
            raise UnknownConnectorError(
                f"Unknown connector type '{connector_type}'. Available: {available}"
            )
        
        try:
            return connector_class(workspace_id, assignment_id)
        except Exception as e:
            logger.error(f"Failed to create {connector_type} connector: {e}")
            raise
    
    @classmethod
    def get_available_connectors(cls) -> list[str]:
        """Get list of available connector types"""
        cls._load_connectors()
        return list(cls._connectors.keys())
    
    @classmethod
    def validate_credentials(cls, connector_type: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate credentials for a connector type
        
        Args:
            connector_type: Type of connector
            credentials: Credentials to validate
            
        Returns:
            Validation result
        """
        try:
            connector = cls.get_connector(connector_type)
            return connector.validate_credentials(credentials)
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @classmethod
    def get_required_fields(cls, connector_type: str) -> list[str]:
        """
        Get required credential fields for a connector type
        
        Args:
            connector_type: Type of connector
            
        Returns:
            List of required field names
        """
        try:
            connector = cls.get_connector(connector_type)
            return connector.get_required_fields()
        except Exception as e:
            logger.error(f"Could not get required fields for {connector_type}: {e}")
            return []
    
    @classmethod
    def register_connector(cls, connector_type: str, connector_class: Type[BaseConnector]):
        """
        Register a new connector type (for plugins/extensions)
        
        Args:
            connector_type: Name of the connector type
            connector_class: Connector class that extends BaseConnector
        """
        cls._load_connectors()
        cls._connectors[connector_type] = connector_class
        logger.info(f"Registered custom connector: {connector_type}")
    
    @classmethod
    def get_connector_info(cls, connector_type: str) -> Dict[str, Any]:
        """
        Get metadata about a connector type
        
        Args:
            connector_type: Type of connector
            
        Returns:
            Connector metadata
        """
        try:
            connector = cls.get_connector(connector_type)
            return {
                "type": connector_type,
                "class": connector.__class__.__name__,
                "required_fields": connector.get_required_fields(),
                "supports_workspace": True,
                "supports_validation": True
            }
        except Exception as e:
            return {"type": connector_type, "error": str(e)}