class EmbeddedGitHubMetrics:
    """GitHub metrics embedded directly in the Flask app"""
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
    def get_repo_metrics(self, org: str, repos: list) -> list:
        """Get GitHub repository metrics for multiple repos"""
        if not self.token:
            return [{"error": "GitHub token not configured"}]
        
        repo_metrics = []
        
        for repo in repos:
            try:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # Get repository info
                repo_url = f"{self.base_url}/repos/{org}/{repo}"
                repo_response = requests.get(repo_url, headers=headers, timeout=10)
                
                if repo_response.status_code != 200:
                    repo_metrics.append({
                        "repo_name": repo,
                        "error": f"GitHub API returned {repo_response.status_code}"
                    })
                    continue
                
                repo_data = repo_response.json()
                
                # Get recent commits (last 30 days)
                since_date = (datetime.now() - timedelta(days=30)).isoformat()
                commits_url = f"{repo_url}/commits?since={since_date}"
                commits_response = requests.get(commits_url, headers=headers, timeout=10)
                commits = commits_response.json() if commits_response.status_code == 200 else []
                
                # Get pull requests
                prs_url = f"{repo_url}/pulls?state=all&per_page=50"
                prs_response = requests.get(prs_url, headers=headers, timeout=10)
                prs = prs_response.json() if prs_response.status_code == 200 else []
                
                repo_metrics.append({
                    "repo_name": repo,
                    "commits_last_30_days": len(commits),
                    "total_prs": len(prs),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "stars": repo_data.get("stargazers_count", 0),
                    "language": repo_data.get("language", "Unknown"),
                    "last_updated": repo_data.get("updated_at", "")
                })
                
            except Exception as e:
                repo_metrics.append({
                    "repo_name": repo,
                    "error": f"GitHub API error: {str(e)}"
                })
        
        return repo_metrics

