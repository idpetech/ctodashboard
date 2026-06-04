"""
Base connector class providing common functionality
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    """
    Abstract base class for all API connectors
    
    Provides common functionality like credential loading, workspace context,
    and standardized interfaces that all connectors must implement.
    """
    
    def __init__(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None):
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        self.credentials = {}
        
        # Load credentials if workspace context is provided
        if workspace_id and assignment_id:
            self._load_workspace_credentials()
        else:
            self._load_environment_credentials()
    
    @abstractmethod
    def get_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get metrics from the external service
        
        Args:
            config: Service-specific configuration
            
        Returns:
            Dictionary containing metrics data
        """
        pass
    
    @abstractmethod
    def validate_credentials(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate credentials against the external service
        
        Args:
            credentials: Dictionary of credential fields
            
        Returns:
            Validation result with 'valid' boolean and optional metadata
        """
        pass
    
    @abstractmethod
    def get_required_fields(self) -> list[str]:
        """
        Get list of required credential fields for this connector
        
        Returns:
            List of required field names
        """
        pass
    
    def _connector_type(self) -> str:
        """Map class name to connector_type (e.g. OpenAIConnector -> openai)."""
        return getattr(self, "CONNECTOR_TYPE", None) or self.__class__.__name__.lower().replace(
            "connector", ""
        )

    def _load_workspace_credentials(self):
        """Load credentials from Postgres credentials table (not metrics_config JSON)."""
        connector_type = self._connector_type()
        try:
            from services.auth.credential_service import CredentialService

            creds = CredentialService().get_workspace_credentials(
                self.workspace_id, self.assignment_id, connector_type
            )
            if creds:
                self.credentials = creds
                logger.info(
                    "Loaded %s credentials from Postgres for %s/%s",
                    connector_type,
                    self.workspace_id,
                    self.assignment_id,
                )
                return
            logger.warning(
                "No Postgres credentials for %s on %s/%s",
                connector_type,
                self.workspace_id,
                self.assignment_id,
            )
        except Exception as e:
            logger.warning("Could not load workspace credentials: %s", e)
        self._load_environment_credentials()
    
    def _load_environment_credentials(self):
        """Load credentials from environment variables - implemented by subclasses"""
        pass
    
    def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Common HTTP request handling with error logging
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object or raises exception
        """
        import requests
        
        try:
            response = requests.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise
    
    def get_connector_type(self) -> str:
        """Get the connector type name"""
        return self.__class__.__name__.lower().replace('connector', '')
    
    def is_configured(self) -> bool:
        """Check if connector has valid credentials"""
        required_fields = self.get_required_fields()
        return all(self.credentials.get(field) for field in required_fields)