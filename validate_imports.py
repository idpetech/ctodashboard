#!/usr/bin/env python3
"""
Validate all Python files can be imported without errors
This catches missing imports, undefined variables, etc.
"""
import sys
import importlib.util
import os

# Change to project directory
os.chdir('/Users/haseebtoor/Projects/ctodashboard')
sys.path.insert(0, '/Users/haseebtoor/Projects/ctodashboard')

files_to_check = [
    ('services.service_manager', 'services/service_manager.py'),
    ('services.embedded.aws_metrics', 'services/embedded/aws_metrics.py'),
    ('services.embedded.github_metrics', 'services/embedded/github_metrics.py'),
    ('services.embedded.jira_metrics', 'services/embedded/jira_metrics.py'),
    ('services.embedded.openai_metrics', 'services/embedded/openai_metrics.py'),
    ('routes.api_routes', 'routes/api_routes.py'),
]

print("=== VALIDATING IMPORTS ===\n")
all_ok = True

for module_name, filepath in files_to_check:
    try:
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        print(f"✓ {filepath}: OK")
    except Exception as e:
        print(f"✗ {filepath}: ERROR")
        print(f"  {type(e).__name__}: {e}")
        all_ok = False

# Now try to import integrated_dashboard
print("\nChecking main file:")
try:
    spec = importlib.util.spec_from_file_location("integrated_dashboard", "integrated_dashboard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print(f"✓ integrated_dashboard.py: OK")
except Exception as e:
    print(f"✗ integrated_dashboard.py: ERROR")
    print(f"  {type(e).__name__}: {e}")
    all_ok = False

if all_ok:
    print("\n✅ ALL FILES CAN BE IMPORTED SUCCESSFULLY")
    sys.exit(0)
else:
    print("\n❌ IMPORT ERRORS FOUND")
    sys.exit(1)
