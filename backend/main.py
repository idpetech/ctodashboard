import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="CTO Dashboard API", version="1.0.0")

# Get frontend URL from environment variable (never hardcode!)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # Environment variable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "CTO Dashboard API", "status": "healthy"}

@app.get("/health")
def health_check():
    from datetime import datetime
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

@app.get("/assignments")
def get_assignments(include_archived: bool = False):
    """Get all assignments from JSON configuration files"""
    from assignment_service import AssignmentService
    
    service = AssignmentService()
    assignments = service.get_all_assignments(include_archived=include_archived)
    
    return assignments

@app.get("/assignments/{assignment_id}")
def get_assignment(assignment_id: str):
    """Get a specific assignment configuration"""
    from assignment_service import AssignmentService
    
    service = AssignmentService()
    assignment = service.get_assignment(assignment_id)
    
    if not assignment:
        return {"error": f"Assignment {assignment_id} not found"}
    
    return assignment

@app.get("/assignments/{assignment_id}/metrics")
async def get_assignment_metrics(assignment_id: str):
    """Get real-time metrics for a specific assignment"""
    from assignment_service import AssignmentService
    from metrics_service import MetricsAggregator
    
    # Get assignment configuration from JSON file
    service = AssignmentService()
    assignment_config = service.get_assignment(assignment_id)
    
    if not assignment_config:
        return {"error": f"Assignment {assignment_id} not found"}
    
    # Get metrics from all configured services
    aggregator = MetricsAggregator()
    metrics = await aggregator.get_all_metrics(assignment_config)
    
    return metrics

@app.get("/assignments/{assignment_id}/cto-insights")
async def get_cto_insights(assignment_id: str):
    """Get detailed CTO-level insights for a specific assignment"""
    from assignment_service import AssignmentService
    from metrics_service import AWSMetrics
    
    # Get assignment configuration
    service = AssignmentService()
    assignment_config = service.get_assignment(assignment_id)
    
    if not assignment_config:
        return {"error": f"Assignment {assignment_id} not found"}
    
    # Get comprehensive AWS insights
    aws_config = assignment_config.get("metrics_config", {}).get("aws", {})
    if not aws_config.get("enabled", False):
        return {"error": "AWS metrics not enabled for this assignment"}
    
    aws_metrics = AWSMetrics()
    comprehensive_report = aws_metrics.get_comprehensive_aws_report()
    
    # Add assignment context
    comprehensive_report["assignment_info"] = {
        "id": assignment_config.get("id"),
        "name": assignment_config.get("name"),
        "monthly_burn_rate": assignment_config.get("monthly_burn_rate"),
        "team_size": assignment_config.get("team_size")
    }
    
    return comprehensive_report

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)