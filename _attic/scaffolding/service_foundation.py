# Phase 2.1: Service Configuration Foundation
# KISS + DRY principles throughout

from datetime import datetime
import requests
import os

class BaseService:
    """Base service class with common functionality"""
    
    def __init__(self, service_id: str, config: dict):
        self.service_id = service_id
        self.config = config
        self.status = "unknown"
        self.last_check = None
        self.error_message = None
    
    def test_connection(self) -> dict:
        """Test service connection - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement test_connection")
    
    def get_metrics(self) -> dict:
        """Get service metrics - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_metrics")
    
    def get_status(self) -> dict:
        """Get service status - common implementation"""
        return {
            "service_id": self.service_id,
            "status": self.status,
            "last_check": self.last_check,
            "error_message": self.error_message,
            "config": self._sanitize_config()
        }
    
    def _sanitize_config(self) -> dict:
        """Remove sensitive data from config"""
        sanitized = self.config.copy()
        for key in ["password", "token", "key", "secret"]:
            if key in sanitized:
                sanitized[key] = "***REDACTED***"
        return sanitized
    
    def _update_status(self, status: str, error_message: str = None):
        """Update service status - common implementation"""
        self.status = status
        self.last_check = datetime.now().isoformat()
        self.error_message = error_message

class InfrastructureService(BaseService):
    """Base class for infrastructure services (AWS, Railway, Vercel)"""
    
    def get_cost_metrics(self) -> dict:
        """Get cost-related metrics"""
        raise NotImplementedError("Infrastructure services must implement get_cost_metrics")
    
    def get_resource_metrics(self) -> dict:
        """Get resource usage metrics"""
        raise NotImplementedError("Infrastructure services must implement get_resource_metrics")

class DevelopmentService(BaseService):
    """Base class for development services (GitHub, GitLab, Bitbucket)"""
    
    def get_repository_metrics(self) -> dict:
        """Get repository-related metrics"""
        raise NotImplementedError("Development services must implement get_repository_metrics")
    
    def get_deployment_metrics(self) -> dict:
        """Get deployment-related metrics"""
        raise NotImplementedError("Development services must implement get_deployment_metrics")

class ProjectManagementService(BaseService):
    """Base class for project management services (Jira, Linear, Asana)"""
    
    def get_issue_metrics(self) -> dict:
        """Get issue-related metrics"""
        raise NotImplementedError("Project management services must implement get_issue_metrics")
    
    def get_sprint_metrics(self) -> dict:
        """Get sprint-related metrics"""
        raise NotImplementedError("Project management services must implement get_sprint_metrics")

class AIService(BaseService):
    """Base class for AI services (OpenAI, Claude, Gemini)"""
    
    def get_usage_metrics(self) -> dict:
        """Get usage-related metrics"""
        raise NotImplementedError("AI services must implement get_usage_metrics")
    
    def get_cost_metrics(self) -> dict:
        """Get cost-related metrics"""
        raise NotImplementedError("AI services must implement get_cost_metrics")

class ServiceFactory:
    """Factory for creating service instances"""
    
    SERVICE_TYPES = {
        "github": "GitHubService",
        "jira": "JiraService", 
        "openai": "OpenAIService",
        "railway": "RailwayService",
        "aws": "AWSService"
    }
    
    @classmethod
    def create_service(cls, service_type: str, service_id: str, config: dict) -> BaseService:
        """Create service instance based on type"""
        if service_type not in cls.SERVICE_TYPES:
            raise ValueError(f"Unknown service type: {service_type}")
        
        # For now, return a placeholder - we'll implement concrete services in Phase 2.2
        return BaseService(service_id, config)
    
    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available service types"""
        return list(cls.SERVICE_TYPES.keys())

class ServiceManager:
    """Simple service manager"""
    
    def __init__(self):
        self.services = {}
        self.factory = ServiceFactory()
    
    def add_service(self, service_type: str, service_id: str, config: dict):
        """Add a new service"""
        service = self.factory.create_service(service_type, service_id, config)
        self.services[service_id] = service
        return service
    
    def get_service(self, service_id: str) -> BaseService:
        """Get service by ID"""
        return self.services.get(service_id)
    
    def test_service(self, service_id: str) -> dict:
        """Test service connection"""
        service = self.get_service(service_id)
        if not service:
            return {"error": "Service not found"}
        
        return service.test_connection()
    
    def get_service_metrics(self, service_id: str) -> dict:
        """Get service metrics"""
        service = self.get_service(service_id)
        if not service:
            return {"error": "Service not found"}
        
        return service.get_metrics()
    
    def get_all_services_status(self) -> dict:
        """Get status of all services"""
        return {
            service_id: service.get_status() 
            for service_id, service in self.services.items()
        }
