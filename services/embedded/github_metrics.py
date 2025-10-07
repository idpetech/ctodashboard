# GitHub Metrics Service
# Extracted from integrated_dashboard.py

import os
import requests
from datetime import datetime

class EmbeddedGitHubMetrics:
    """GitHub metrics embedded directly in the Flask app"""
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
    def get_repo_metrics(self, org: str, repos: list) -> list:
        """Get GitHub repository metrics for multiple repos"""
        if not self.token:
            return [{"error": "GitHub token not configured"}]
        
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
                
                if response.status_code != 200:
                    results.append({
                        "repo_name": repo,
                        "error": f"HTTP {response.status_code}"
                    })
                    continue
                
                repo_data = response.json()
                
                # Get commits (last 30 days)
                since_date = (datetime.now() - datetime.timedelta(days=30)).isoformat()
                commits_url = f"{repo_url}/commits?since={since_date}"
                commits_response = requests.get(commits_url, headers=headers, timeout=10)
                commits_count = len(commits_response.json()) if commits_response.status_code == 200 else 0
                
                results.append({
                    "repo_name": repo,
                    "stars": repo_data.get("stargazers_count", 0),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "language": repo_data.get("language", "Unknown"),
                    "last_updated": repo_data.get("updated_at"),
                    "commits_last_30_days": commits_count,
                    "total_prs": 0  # Would need additional API call
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
        return self.get_repo_metrics(org, repos)
