"""
Connector-specific exceptions
"""

class ConnectorError(Exception):
    """Base exception for all connector errors"""
    pass

class ValidationError(ConnectorError):
    """Exception raised when connector validation fails"""
    pass

class UnknownConnectorError(ConnectorError):
    """Exception raised when trying to use an unknown connector type"""
    pass

class CredentialsError(ConnectorError):
    """Exception raised when connector credentials are invalid"""
    pass

class APIError(ConnectorError):
    """Exception raised when external API calls fail"""
    pass