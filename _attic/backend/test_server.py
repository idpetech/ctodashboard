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
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5176")
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

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "github": "configured" if os.getenv("GITHUB_TOKEN") else "not_configured",
            "jira": "configured" if os.getenv("JIRA_TOKEN") else "not_configured", 
            "aws": "configured" if os.getenv("AWS_ACCESS_KEY_ID") else "not_configured",
            "railway": "configured" if os.getenv("RAILWAY_TOKEN") else "not_configured"
        }
    }

def get_github_repo_data(org: str, repo: str):
    """Simple GitHub API call"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"error": "No GitHub token"}
    
    url = f"https://api.github.com/repos/{org}/{repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "repo_name": repo,
                "language": data.get("language"),
                "stars": data.get("stargazers_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "last_updated": data.get("updated_at", ""),
                "commits_30d": 0  # Simplified for now
            }
        else:
            return {"error": f"GitHub API {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"error": f"GitHub error: {str(e)}"}

def get_aws_data():
    """Simple AWS Cost Explorer call"""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    if not all([access_key, secret_key]):
        return {"error": "AWS credentials missing"}
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        ce_client = boto3.client(
            'ce',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Get cost for last 30 days
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        total_cost = 0
        services = {}
        for result in response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service_name = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                services[service_name] = cost
                total_cost += cost
        
        return {
            "total_cost_30d": round(total_cost, 2),
            "currency": "USD",
            "top_services": dict(sorted(services.items(), key=lambda x: x[1], reverse=True)[:5]),
            "period": f"{start_date} to {end_date}"
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            return {"error": "AWS permissions needed - add Cost Explorer access to your IAM user"}
        return {"error": f"AWS API error: {str(e)}"}
    except Exception as e:
        return {"error": f"AWS connection error: {str(e)}"}

def get_railway_data():
    """Simple Railway API call"""
    token = os.getenv("RAILWAY_TOKEN")
    project_id = os.getenv("RAILWAY_PROJECT_ID")
    
    if not token:
        return {"error": "Railway token missing"}
    
    try:
        import aiohttp
        import asyncio
        import ssl
        
        async def fetch_railway():
            # Handle SSL issues
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            query = '''
            query {
                projects {
                    edges {
                        node {
                            id
                            name
                            deployments(first: 5) {
                                edges {
                                    node {
                                        id
                                        status
                                        createdAt
                                    }
                                }
                            }
                        }
                    }
                }
            }
            '''
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    "https://backboard.railway.app/graphql",
                    headers=headers,
                    json={"query": query}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "errors" in data:
                            return {"error": f"Railway GraphQL error: {data['errors']}"}
                        
                        projects = data.get("data", {}).get("projects", {}).get("edges", [])
                        if projects:
                            project = projects[0]["node"]
                            deployments = project.get("deployments", {}).get("edges", [])
                            return {
                                "project_name": project.get("name", "Unknown"),
                                "total_deployments": len(deployments),
                                "latest_deployments": [d["node"]["status"] for d in deployments[:3]]
                            }
                        return {"error": "No Railway projects found"}
                    else:
                        text = await response.text()
                        return {"error": f"Railway API {response.status}: {text[:200]}"}
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(fetch_railway())
        finally:
            loop.close()
            
    except Exception as e:
        return {"error": f"Railway error: {str(e)}"}

def get_jira_data():
    """Simple Jira API call"""
    base_url = os.getenv("JIRA_URL")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_TOKEN")
    
    if not all([base_url, email, token]):
        return {"error": "Jira credentials missing"}
    
    try:
        auth = (email, token)
        headers = {"Accept": "application/json"}
        
        # Get issues for MFLP project
        search_url = f"{base_url}/rest/api/3/search"
        jql_query = "project = 'MFLP' AND created >= -30d"
        params = {
            "jql": jql_query,
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
                "total_issues_30d": total,
                "resolved_issues_30d": resolved,
                "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 0
            }
        else:
            return {"error": f"Jira API {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"error": f"Jira error: {str(e)}"}

@app.get("/test-metrics")
def test_metrics():
    """Test all APIs directly"""
    
    # Test GitHub
    github_results = []
    for repo in ["idpetech_portal", "resumehealth-checker"]:
        result = get_github_repo_data("idpetech", repo)
        github_results.append(result)
    
    # Test Jira
    jira_result = get_jira_data()
    
    # Test AWS
    aws_result = get_aws_data()
    
    # Test Railway
    railway_result = get_railway_data()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "github": github_results,
        "jira": jira_result,
        "aws": aws_result,
        "railway": railway_result,
        "environment_check": {
            "github_token_length": len(os.getenv("GITHUB_TOKEN", "")) if os.getenv("GITHUB_TOKEN") else 0,
            "jira_url": os.getenv("JIRA_URL", "not_set"),
            "jira_email": os.getenv("JIRA_EMAIL", "not_set"),
        }
    }

@app.get("/assignments/ideptech/metrics")
def get_ideptech_metrics():
    """Simplified metrics endpoint for testing"""
    metrics = test_metrics()
    # Format response to match what frontend expects
    return {
        "timestamp": metrics["timestamp"],
        "assignment_id": "ideptech",
        "github": metrics["github"],
        "jira": metrics["jira"],
        "aws": metrics.get("aws", {"error": "AWS permissions needed"}),
        "railway": metrics.get("railway", {"error": "Railway API needs adjustment"})
    }

@app.get("/assignments")
def get_assignments():
    """Return hardcoded assignment for testing"""
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
            "github": {"enabled": True, "org": "idpetech", "repos": ["idpetech_portal", "resumehealth-checker"]},
            "jira": {"enabled": True, "project_key": "MFLP"},
            "aws": {"enabled": True},
            "railway": {"enabled": True}
        },
        "team": {
            "roles": ["Frontend Dev", "Backend Dev", "DevOps", "QA"],
            "tech_stack": ["React", "Node.js", "PostgreSQL", "AWS", "Docker"]
        }
    }]

if __name__ == "__main__":
    import uvicorn
    print("Starting test server with environment variables loaded...")
    print(f"GitHub token: {'✅' if os.getenv('GITHUB_TOKEN') else '❌'}")
    print(f"Jira configured: {'✅' if os.getenv('JIRA_TOKEN') else '❌'}")
    uvicorn.run(app, host="0.0.0.0", port=8000)