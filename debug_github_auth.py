#!/usr/bin/env python3
"""
GitHub Authentication Diagnostic Tool
Helps diagnose and fix GitHub API authentication issues in CTO Dashboard
"""

import os
from dotenv import load_dotenv

def main():
    print("🔍 GitHub Authentication Diagnostic Tool")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("❌ .env file not found")
        print("💡 Create a .env file from .env.example:")
        print("   cp .env.example .env")
        return
    
    # Check GITHUB_TOKEN
    token = os.getenv('GITHUB_TOKEN')
    
    print("\n📋 Environment Variable Check:")
    if not token:
        print("❌ GITHUB_TOKEN not found in environment")
        print("💡 Add GITHUB_TOKEN to your .env file")
        return
    elif token == "test_token":
        print(f"⚠️  GITHUB_TOKEN is placeholder: '{token}'")
        print("💡 Replace with real GitHub Personal Access Token")
        print("   1. Go to https://github.com/settings/tokens")
        print("   2. Click 'Generate new token (classic)'")
        print("   3. Select 'repo' scope for repository access")
        print("   4. Copy token and update GITHUB_TOKEN in .env file")
        return
    elif len(token) < 20:
        print(f"❌ GITHUB_TOKEN too short: {len(token)} characters")
        print("💡 GitHub tokens should be 40+ characters")
        print("   Generate new token at https://github.com/settings/tokens")
        return
    else:
        print(f"✅ GITHUB_TOKEN found: {token[:7]}...")
        print(f"📏 Length: {len(token)} characters")
    
    # Test token format
    if token.startswith('ghp_'):
        print("🔑 Classic Personal Access Token detected")
    elif token.startswith('github_pat_'):
        print("🔑 Fine-grained Personal Access Token detected")
    else:
        print("⚠️  Unknown token format")
    
    # Test GitHub API connectivity
    print("\n🌐 Testing GitHub API connectivity...")
    
    try:
        from services.embedded.github_metrics import EmbeddedGitHubMetrics
        
        github_service = EmbeddedGitHubMetrics()
        validation = github_service.validate_token()
        
        if validation['valid']:
            print("✅ GitHub API authentication successful!")
            print(f"👤 Authenticated as: {validation['authenticated_user']}")
            print(f"⏱️  Rate limit remaining: {validation['rate_limit_remaining']}")
            print(f"🔑 Token type: {validation['token_type']}")
            
            # Test basic repository access
            print("\n📊 Testing repository metrics...")
            test_config = {
                'org': validation['authenticated_user'],
                'repos': []
            }
            
            # Try to get user's repositories to test
            import requests
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            repos_response = requests.get('https://api.github.com/user/repos?per_page=5', headers=headers)
            if repos_response.status_code == 200:
                user_repos = [repo['name'] for repo in repos_response.json()]
                if user_repos:
                    test_config['repos'] = user_repos[:2]  # Test with first 2 repos
                    print(f"🧪 Testing with repositories: {test_config['repos']}")
                    metrics = github_service.get_metrics(test_config)
                    
                    if any('error' in metric for metric in metrics):
                        print("⚠️  Some repositories returned errors:")
                        for metric in metrics:
                            if 'error' in metric:
                                print(f"   - {metric.get('repo_name', 'unknown')}: {metric['error']}")
                    else:
                        print("✅ Repository metrics working correctly!")
                        print(f"📈 Retrieved data for {len(metrics)} repositories")
                else:
                    print("ℹ️  No repositories found in your account")
            else:
                print(f"⚠️  Could not retrieve your repositories: {repos_response.status_code}")
                
        else:
            print("❌ GitHub API authentication failed!")
            print(f"🔍 Error: {validation['error']}")
            print(f"💡 {validation['instructions']}")
            
    except ImportError as e:
        print(f"❌ Could not import GitHub service: {e}")
        print("💡 Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n📋 Summary:")
    print("   For HTTP 401 errors, the most common causes are:")
    print("   1. Using 'test_token' placeholder instead of real token")
    print("   2. Token expired or revoked")
    print("   3. Token missing required 'repo' scope")
    print("   4. Token format incorrect")
    print()
    print("   🔗 Generate new token: https://github.com/settings/tokens")
    print("   📚 GitHub API docs: https://docs.github.com/en/rest")

if __name__ == "__main__":
    main()