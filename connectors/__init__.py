"""
Connector Package - Modular API integrations

This package provides a clean, modular architecture for external API connectors.
Each connector is self-contained with its own validation, models, and business logic.
"""

from .registry import ConnectorRegistry

__all__ = ['ConnectorRegistry']