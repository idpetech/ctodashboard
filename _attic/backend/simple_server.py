#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta

# Load environment variables FIRST
load_dotenv()

app = FastAPI(title="CTO Dashboard API", version="1.0.0")

# CORS setup  
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "CTO Dashboard API", "status": "healthy"}

@app.get("/assignments")
def get_assignments():
    """Return assignment data matching frontend expectations"""
    return [{
        "id": "ideptech",
        "name": "IdepTech Consulting", 
        "status": "active",
        "start_date": "2024-01-15",
        "end_date": None,
        "monthly_burn_rate": 25000,
        "team_size": 8,
        "description": "Full-stack development consulting engagement",
        "metrics_config": {
            "github": {"enabled": True, "org": "idpetech", "repos": ["idpetech_portal", "IDPETech-portal"]},
            "jira": {"enabled": True, "project_key": "MFLP"},
            "aws": {"enabled": True},
            "railway": {"enabled": True}
        },
        "team": {
            "roles": ["Frontend Dev", "Backend Dev", "DevOps", "QA"],
            "tech_stack": ["React", "Node.js", "PostgreSQL", "AWS", "Docker"]
        }
    }]

def get_github_repo_metrics(org: str, repo: str):
    """Get GitHub repository metrics"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"error": "No GitHub token configured"}
    
    try:
        url = f"https://api.github.com/repos/{org}/{repo}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "repo_name": repo,
                "commits_last_30_days": 0,  # Simplified for stability
                "total_prs": 0,
                "open_issues": data.get("open_issues_count", 0),
                "stars": data.get("stargazers_count", 0),
                "language": data.get("language", "Unknown"),
                "last_updated": data.get("updated_at", "")
            }
        else:
            return {"error": f"GitHub API returned {response.status_code}"}
    except Exception as e:
        return {"error": f"GitHub API error: {str(e)}"}

def get_jira_metrics():
    """Get Jira project metrics"""
    base_url = os.getenv("JIRA_URL")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_TOKEN")
    
    if not all([base_url, email, token]):
        return {"error": "Jira credentials not configured"}
    
    try:
        auth = (email, token)
        headers = {"Accept": "application/json"}
        
        search_url = f"{base_url}/rest/api/3/search"
        params = {
            "jql": "project = 'MFLP' AND created >= -30d",
            "fields": "status,created,resolutiondate"
        }
        
        response = requests.get(search_url, auth=auth, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            issues = data.get("issues", [])
            total = len(issues)
            resolved = len([i for i in issues if i["fields"].get("resolutiondate")])
            
            return {
                "project_key": "MFLP",
                "project_name": "ResumeAI",
                "total_issues_last_30_days": total,
                "resolved_issues_last_30_days": resolved,
                "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 0
            }
        else:
            return {"error": f"Jira API returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Jira API error: {str(e)}"}

@app.get("/assignments/ideptech/metrics")
def get_assignment_metrics():
    """Get metrics in the exact format the frontend expects"""
    
    # Get GitHub metrics
    github_data = []
    for repo in ["idpetech_portal", "IDPETech-portal"]:
        repo_metrics = get_github_repo_metrics("idpetech", repo)
        github_data.append(repo_metrics)
    
    # Get Jira metrics
    jira_data = get_jira_metrics()
    
    # Return in exact format frontend expects
    return {
        "timestamp": datetime.now().isoformat(),
        "assignment_id": "ideptech",
        "github": github_data,
        "jira": jira_data,
        "aws": {"error": "AWS API error: User needs ce:GetCostAndUsage permission"},
        "railway": {"error": "Railway API error: API endpoint needs adjustment"}
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CTO Dashboard API server...")
    print(f"📊 GitHub: {'✅ Ready' if os.getenv('GITHUB_TOKEN') else '❌ No token'}")
    print(f"🎯 Jira: {'✅ Ready' if os.getenv('JIRA_TOKEN') else '❌ No token'}")
    print(f"🌐 Frontend: {FRONTEND_URL}")
    uvicorn.run(app, host="0.0.0.0", port=8000)