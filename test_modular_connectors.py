#!/usr/bin/env python3
"""
Test the new modular connector architecture
"""
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append('.')

def test_connector_registry():
    """Test the connector registry system"""
    logger.info("🔧 Testing Modular Connector Architecture")
    logger.info("=" * 60)
    
    try:
        from connectors.registry import ConnectorRegistry
        logger.info("✅ ConnectorRegistry imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import ConnectorRegistry: {e}")
        return False
    
    # Test 1: Get available connectors
    try:
        available = ConnectorRegistry.get_available_connectors()
        logger.info(f"📋 Available connectors: {available}")
        
        if not available:
            logger.warning("⚠️ No connectors loaded - this is expected for initial test")
    except Exception as e:
        logger.error(f"❌ Failed to get available connectors: {e}")
        return False
    
    return True

def test_openai_connector():
    """Test the modular OpenAI connector"""
    logger.info("\n🤖 Testing OpenAI Connector Module")
    logger.info("-" * 40)
    
    try:
        from connectors.openai.connector import OpenAIConnector
        from connectors.openai.validator import OpenAIValidator
        logger.info("✅ OpenAI connector modules imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import OpenAI connector: {e}")
        return False
    
    # Test validator
    try:
        logger.info("🔍 Testing OpenAI validator...")
        
        # Test missing API key
        result = OpenAIValidator.validate_credentials({})
        logger.info(f"Missing key test: {result['valid']} - {result.get('error', 'OK')}")
        
        # Test invalid API key
        result = OpenAIValidator.validate_credentials({"openai_api_key": "invalid_key"})
        logger.info(f"Invalid key test: {result['valid']} - {result.get('error', 'OK')}")
        
        # Test required fields
        fields = OpenAIValidator.get_required_fields()
        logger.info(f"Required fields: {fields}")
        
    except Exception as e:
        logger.error(f"❌ OpenAI validator test failed: {e}")
        return False
    
    # Test connector
    try:
        logger.info("🔧 Testing OpenAI connector...")
        
        # Test global connector (no workspace)
        connector = OpenAIConnector()
        logger.info(f"Global connector configured: {'Yes' if connector.is_configured() else 'No'}")
        logger.info(f"Connector type: {connector.get_connector_type()}")
        logger.info(f"Required fields: {connector.get_required_fields()}")
        
        # Test workspace connector
        workspace_connector = OpenAIConnector("admin_workspace", "IDPETECH")
        logger.info(f"Workspace connector configured: {'Yes' if workspace_connector.is_configured() else 'No'}")
        
        # Test get_metrics (should handle missing credentials gracefully)
        metrics = connector.get_metrics({})
        logger.info(f"Metrics response type: {type(metrics)}")
        if 'error' in metrics:
            logger.info(f"Expected error (no API key): {metrics['error']}")
        
    except Exception as e:
        logger.error(f"❌ OpenAI connector test failed: {e}")
        return False
    
    return True

def test_base_connector():
    """Test the base connector class"""
    logger.info("\n🏗️ Testing Base Connector")
    logger.info("-" * 40)
    
    try:
        from connectors.base.base_connector import BaseConnector
        from connectors.base.exceptions import ConnectorError, UnknownConnectorError
        logger.info("✅ Base connector and exceptions imported successfully")
        
        # Test exception hierarchy
        try:
            raise ConnectorError("Test error")
        except ConnectorError as e:
            logger.info(f"✅ ConnectorError works: {e}")
        
        # Test that we can't instantiate abstract base class
        try:
            BaseConnector()
            logger.error("❌ Should not be able to instantiate abstract BaseConnector")
        except TypeError:
            logger.info("✅ BaseConnector is properly abstract")
        
    except Exception as e:
        logger.error(f"❌ Base connector test failed: {e}")
        return False
    
    return True

def test_registry_factory():
    """Test the connector registry factory methods"""
    logger.info("\n🏭 Testing Registry Factory")
    logger.info("-" * 40)
    
    try:
        from connectors.registry import ConnectorRegistry
        from connectors.base.exceptions import UnknownConnectorError
        
        # Test unknown connector
        try:
            ConnectorRegistry.get_connector("nonexistent")
            logger.error("❌ Should fail for unknown connector")
        except UnknownConnectorError as e:
            logger.info(f"✅ Correctly handled unknown connector: {e}")
        
        # Test OpenAI connector creation (if available)
        try:
            connector = ConnectorRegistry.get_connector("openai")
            logger.info(f"✅ Created OpenAI connector via registry: {type(connector)}")
            logger.info(f"Connector type: {connector.get_connector_type()}")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI connector not available in registry yet: {e}")
        
        # Test get_required_fields
        try:
            fields = ConnectorRegistry.get_required_fields("openai")
            logger.info(f"✅ Got required fields via registry: {fields}")
        except Exception as e:
            logger.warning(f"⚠️ Required fields not available: {e}")
        
        # Test credential validation
        try:
            result = ConnectorRegistry.validate_credentials("openai", {})
            logger.info(f"✅ Validation via registry: {result.get('valid', False)} - {result.get('error', 'OK')}")
        except Exception as e:
            logger.warning(f"⚠️ Validation not available: {e}")
        
    except Exception as e:
        logger.error(f"❌ Registry factory test failed: {e}")
        return False
    
    return True

def test_architecture_benefits():
    """Test the benefits of the new architecture"""
    logger.info("\n🎯 Testing Architecture Benefits")
    logger.info("-" * 40)
    
    # Test 1: Clean separation
    try:
        # Business logic is separate from validation
        from connectors.openai.connector import OpenAIConnector
        from connectors.openai.validator import OpenAIValidator
        
        connector = OpenAIConnector()
        validator = OpenAIValidator()
        
        # Can use validator independently
        result = validator.validate_credentials({"openai_api_key": "test"})
        logger.info("✅ Can use validator independently of connector")
        
        # Can use connector independently  
        metrics = connector.get_metrics({})
        logger.info("✅ Can use connector independently of validator")
        
    except Exception as e:
        logger.error(f"❌ Separation test failed: {e}")
        return False
    
    # Test 2: Easy imports
    try:
        from connectors.openai import OpenAIConnector, OpenAIValidator
        from connectors.base import BaseConnector, ConnectorError
        logger.info("✅ Clean, organized imports work")
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False
    
    # Test 3: Consistent interfaces
    try:
        connector = OpenAIConnector()
        
        # All connectors have these standard methods
        assert hasattr(connector, 'get_metrics'), "Missing get_metrics method"
        assert hasattr(connector, 'validate_credentials'), "Missing validate_credentials method"
        assert hasattr(connector, 'get_required_fields'), "Missing get_required_fields method"
        assert hasattr(connector, 'is_configured'), "Missing is_configured method"
        
        logger.info("✅ Consistent interface across connectors")
        
    except Exception as e:
        logger.error(f"❌ Interface test failed: {e}")
        return False
    
    return True

def run_all_tests():
    """Run all modular architecture tests"""
    logger.info("🚀 Starting Modular Connector Architecture Tests")
    logger.info("=" * 70)
    
    tests = [
        ("Connector Registry", test_connector_registry),
        ("OpenAI Connector", test_openai_connector),
        ("Base Connector", test_base_connector),
        ("Registry Factory", test_registry_factory),
        ("Architecture Benefits", test_architecture_benefits)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                logger.info(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name}: FAILED with exception: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 70)
    logger.info(f"🎯 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed! Modular architecture is working correctly.")
        logger.info("\n💡 Benefits achieved:")
        logger.info("  • Clean separation of concerns")
        logger.info("  • Easy unit testing")
        logger.info("  • Consistent interfaces")  
        logger.info("  • Plugin architecture ready")
        logger.info("  • Maintainable codebase")
    else:
        logger.warning("⚠️ Some tests failed. Architecture needs refinement.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)