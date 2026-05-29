# GitHub Metrics Service
# Extracted from integrated_dashboard.py

import os
import requests
from datetime import datetime, timedelta

class EmbeddedGitHubMetrics:
    """GitHub metrics embedded directly in the Flask app"""
    
    def __init__(self, workspace_id=None, assignment_id=None):
        # Phase 3: Support workspace credentials with environment variable fallback
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        
        # Initialize credentials (preserves existing behavior if no workspace context)
        self._init_credentials()
        self.base_url = "https://api.github.com"
    
    def _init_credentials(self):
        """Initialize GitHub credentials with workspace support and env var fallback"""
        if self.workspace_id and self.assignment_id:
            try:
                from services.auth.credential_service import CredentialService
                credential_service = CredentialService()
                credentials = credential_service.get_github_credentials(self.workspace_id, self.assignment_id)
                self.token = credentials.get("token") or os.getenv("GITHUB_TOKEN")
                self.org = credentials.get("org") or os.getenv("GITHUB_ORG")
            except Exception as e:
                print(f"Warning: Could not load workspace credentials, falling back to env vars: {e}")
                self.token = os.getenv("GITHUB_TOKEN")
                self.org = os.getenv("GITHUB_ORG")
        else:
            # Fallback to environment variables (preserves existing behavior)
            self.token = os.getenv("GITHUB_TOKEN")
            self.org = os.getenv("GITHUB_ORG")
    
    def validate_token(self) -> dict:
        """Validate GitHub token and return status information"""
        if not self.token:
            return {
                "valid": False,
                "error": "No GITHUB_TOKEN environment variable found",
                "instructions": "Set GITHUB_TOKEN environment variable with a valid GitHub Personal Access Token"
            }
        
        if self.token == "test_token":
            return {
                "valid": False, 
                "error": "GITHUB_TOKEN is set to placeholder value 'test_token'",
                "instructions": "Replace with a valid GitHub Personal Access Token from https://github.com/settings/tokens"
            }
        
        if len(self.token) < 20:
            return {
                "valid": False,
                "error": f"GITHUB_TOKEN appears to be too short ({len(self.token)} characters)",
                "instructions": "GitHub Personal Access Tokens should be 40+ characters. Generate a new one at https://github.com/settings/tokens"
            }
        
        # Test token with GitHub API
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CTO-Dashboard/1.0"
        }
        
        try:
            response = requests.get(f"{self.base_url}/user", headers=headers, timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "valid": True,
                    "authenticated_user": user_data.get("login"),
                    "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
                    "token_type": "Classic PAT" if self.token.startswith("ghp_") else "Fine-grained PAT" if self.token.startswith("github_pat_") else "Unknown"
                }
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "error": "GitHub API returned 401 - Invalid credentials",
                    "instructions": "Generate a new GitHub Personal Access Token at https://github.com/settings/tokens with 'repo' scope"
                }
            else:
                return {
                    "valid": False,
                    "error": f"GitHub API returned {response.status_code}: {response.text[:100]}",
                    "instructions": "Check token permissions and GitHub API status"
                }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Connection error: {str(e)}",
                "instructions": "Check internet connection and GitHub API availability"
            }
        
    def get_repo_metrics(self, org: str, repos: list) -> list:
        """Get GitHub repository metrics for multiple repos"""
        if not self.token or self.token == "test_token" or len(self.token) < 20:
            return [{"error": "Valid GitHub token not configured"}]
        
        results = []
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        for repo in repos:
            try:
                # Get repository details
                repo_url = f"{self.base_url}/repos/{org}/{repo}"
                response = requests.get(repo_url, headers=headers, timeout=10)
                
                if response.status_code == 401:
                    results.append({
                        "repo_name": repo,
                        "error": "HTTP 401 - Invalid GitHub token. Please check your GITHUB_TOKEN environment variable."
                    })
                    continue
                elif response.status_code != 200:
                    results.append({
                        "repo_name": repo,
                        "error": f"HTTP {response.status_code}: {response.text[:100] if response.text else 'Unknown error'}"
                    })
                    continue
                
                repo_data = response.json()
                
                # Get commits (last 30 days) - FIXED: proper timedelta import
                since_date = (datetime.now() - timedelta(days=30)).isoformat()
                commits_url = f"{repo_url}/commits?since={since_date}"
                commits_response = requests.get(commits_url, headers=headers, timeout=10)
                commits_count = len(commits_response.json()) if commits_response.status_code == 200 else 0
                
                # Get pull requests - ADDED: missing total_prs implementation
                prs_url = f"{repo_url}/pulls?state=all&per_page=50"
                prs_response = requests.get(prs_url, headers=headers, timeout=10)
                total_prs = len(prs_response.json()) if prs_response.status_code == 200 else 0
                
                results.append({
                    "repo_name": repo,
                    "stars": repo_data.get("stargazers_count", 0),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "language": repo_data.get("language", "Unknown"),
                    "last_updated": repo_data.get("updated_at"),
                    "commits_last_30_days": commits_count,
                    "total_prs": total_prs
                })
                
            except Exception as e:
                results.append({
                    "repo_name": repo,
                    "error": str(e)
                })
        
        return results
    
    def get_metrics(self, config: dict) -> list:
        """Get GitHub metrics based on configuration"""
        org = config.get("org", "")
        repos = config.get("repos", [])
        
        if not org:
            return [{"error": "GitHub organization not configured"}]
        if not repos:
            return [{"error": "No repositories configured"}]
            
        return self.get_repo_metrics(org, repos)
