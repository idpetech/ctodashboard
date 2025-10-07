#!/usr/bin/env python3
"""
Static analysis to find common issues without importing
"""
import ast
import sys

def check_file(filepath):
    """Check a file for common issues"""
    errors = []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content, filepath)
    except SyntaxError as e:
        return [f"Syntax error at line {e.lineno}: {e.msg}"]
    
    # Find all imports
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module.split('.')[0])
    
    # Find all name references
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
    
    # Common modules that should be imported
    common_modules = {
        'os': ['getenv', 'path', 'environ'],
        'sys': ['argv', 'exit', 'path'],
        'json': ['loads', 'dumps', 'load', 'dump'],
        'requests': ['get', 'post', 'put', 'delete'],
        'datetime': ['datetime', 'timedelta', 'date'],
    }
    
    # Check for likely missing imports
    for module, indicators in common_modules.items():
        # If we use module directly (e.g., os.getenv)
        if module in used_names and module not in imported_names:
            errors.append(f"Likely missing: import {module}")
    
    return errors

files_to_check = [
    'integrated_dashboard.py',
    'routes/api_routes.py',
    'services/service_manager.py',
    'services/embedded/aws_metrics.py',
    'services/embedded/github_metrics.py',
    'services/embedded/jira_metrics.py',
    'services/embedded/openai_metrics.py',
]

print("=== STATIC ANALYSIS ===\n")
all_ok = True

for filepath in files_to_check:
    errors = check_file(filepath)
    if errors:
        print(f"✗ {filepath}:")
        for error in errors:
            print(f"  {error}")
        all_ok = False
    else:
        print(f"✓ {filepath}: OK")

if all_ok:
    print("\n✅ NO ISSUES FOUND")
else:
    print("\n❌ ISSUES FOUND")
    sys.exit(1)
