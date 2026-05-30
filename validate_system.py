#!/usr/bin/env python3
"""
System Validation Script - Phase 0 Safety Check
Run this to ensure existing functionality is preserved during workspace implementation
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.workspace.validation import SystemValidator
from services.workspace.workspace_service import WorkspaceService

def main():
    print("=" * 60)
    print("CTO DASHBOARD - SYSTEM VALIDATION")
    print("Phase 0: Foundation Safety Check")
    print("=" * 60)
    print()
    
    # Initialize validator
    validator = SystemValidator()
    
    # Run validation suite
    print("Running complete system validation...")
    print()
    
    # Generate and display report
    report = validator.generate_validation_report()
    print(report)
    
    # Additional workspace readiness check
    print("=" * 60)
    print("WORKSPACE READINESS ASSESSMENT")
    print("=" * 60)
    print()
    
    workspace_service = WorkspaceService()
    
    # Current structure analysis
    print("📊 CURRENT STRUCTURE ANALYSIS")
    analysis = workspace_service.analyze_current_structure()
    print(f"  Total assignments: {analysis['total_assignments']}")
    print(f"  Connector types used: {', '.join(analysis['connector_types_used'])}")
    print(f"  Unique organizations: {analysis['total_assignments']}")
    print()
    
    # Migration readiness
    print("🚀 MIGRATION READINESS")
    readiness = workspace_service.get_workspace_readiness()
    print(f"  Ready for migration: {readiness['ready_for_migration']}")
    print(f"  Migration complexity: {readiness['migration_complexity']}")
    
    if readiness['warnings']:
        print("  ⚠️  Warnings:")
        for warning in readiness['warnings']:
            print(f"    - {warning}")
            
    if readiness['recommendations']:
        print("  💡 Recommendations:")
        for rec in readiness['recommendations']:
            print(f"    - {rec}")
    print()
    
    # Workspace preview
    print("🔮 WORKSPACE STRUCTURE PREVIEW")
    preview = workspace_service.preview_workspace_structure()
    print(f"  Suggested workspaces: {preview['total_workspaces']}")
    print(f"  Assignments to migrate: {preview['migration_summary']['assignments_to_migrate']}")
    print(f"  Connector templates needed: {preview['migration_summary']['estimated_templates_needed']}")
    print()
    
    # Legacy compatibility check
    print("🔒 LEGACY COMPATIBILITY CHECK")
    compatibility = workspace_service.validate_legacy_compatibility()
    print(f"  Legacy loading works: {compatibility['legacy_loading_works']}")
    print(f"  Assignments readable: {compatibility['assignments_readable']}")
    print(f"  Assignments with errors: {compatibility['assignments_with_errors']}")
    
    if compatibility['errors']:
        print("  ❌ Errors found:")
        for error in compatibility['errors']:
            print(f"    - {error}")
    else:
        print("  ✅ No compatibility issues detected")
    
    print()
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    
    # Determine overall status
    validation_results = validator.validate_all()
    if validation_results['overall_status'] == 'pass' and compatibility['legacy_loading_works']:
        print("✅ System is healthy and ready for Phase 1")
        return 0
    else:
        print("❌ System validation failed - address issues before proceeding")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)