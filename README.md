# CTO Dashboard

A comprehensive executive dashboard for tracking project metrics, costs, and strategic insights across multiple platforms including GitHub, Jira, AWS, and Railway.

## 🎯 Overview

The CTO Dashboard provides real-time visibility into:
- **Project metrics** from GitHub repositories
- **Issue tracking** from Jira projects  
- **Cloud infrastructure costs** from AWS services
- **Deployment metrics** from Railway projects
- **Comprehensive CTO insights** with cost optimization recommendations

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │  External APIs  │
│   React/Vite    │◄──►│   FastAPI       │◄──►│  GitHub, Jira   │
│   TypeScript    │    │   Python        │    │  AWS, Railway   │
│   Tailwind CSS  │    │   Async         │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tech Stack

**Frontend:**
- React 18 with TypeScript
- Vite for fast development and building
- Tailwind CSS for styling
- Modern fetch API for HTTP requests

**Backend:**
- FastAPI (Python 3.8+)
- Async/await for concurrent API calls
- Pydantic for data validation
- CORS middleware for cross-origin requests

**External Integrations:**
- GitHub API v4 (GraphQL)
- Jira REST API v3
- AWS Boto3 (Cost Explorer, EC2, S3, Route53, RDS, Lightsail)
- Railway API

## 🚀 Features

### Executive Dashboard
- **Multi-project overview** with assignment cards
- **Real-time metrics** from all configured services
- **Cost tracking** with trend analysis
- **Team and technology stack** visibility

### GitHub Integration
- Repository activity tracking
- Commit frequency analysis
- Pull request metrics
- Issue statistics
- Language and technology insights

### Jira Integration
- Project issue tracking
- Resolution rate analysis
- Sprint performance metrics
- Team productivity insights

### AWS Cost Management
- **30-day cost analysis** with daily breakdowns
- **Service-by-service** cost breakdown
- **Resource inventory** across all major AWS services:
  - EC2 instances with state and cost information
  - Route 53 hosted zones with record counts
  - S3 buckets with size and usage metrics
  - RDS databases with engine and cost details
  - Lightsail instances and pricing
- **Weekly cost trends** with visual charts
- **CTO-level strategic recommendations** for optimization

### Railway Deployment Tracking
- Deployment success rates
- Project performance metrics
- Build and deployment history

### Advanced CTO Insights
- **Cost optimization recommendations** with potential savings
- **Resource utilization analysis** 
- **Strategic planning insights** with actionable priorities
- **Risk assessment** and red flag identification

## 📋 Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **API Access** to configured services (GitHub, Jira, AWS, Railway)

## ⚙️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ctodashboard
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Create and configure environment file
cp .env.example .env
# Edit .env with your API credentials (see Configuration section)
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Assignment Configuration
```bash
# Create assignment JSON files in backend/assignments/
# Example: backend/assignments/my-project.json
```

## 🔧 Configuration

### Environment Variables (.env)

Create a `.env` file in the `backend/` directory:

```env
# Frontend URL for CORS
FRONTEND_URL=http://localhost:5173

# GitHub API
GITHUB_TOKEN=ghp_your_github_personal_access_token
GITHUB_ORG=your-github-organization

# Jira API
JIRA_TOKEN=your_jira_api_token
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com

# AWS API
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Railway API
RAILWAY_TOKEN=your_railway_api_token
RAILWAY_PROJECT_ID=your_railway_project_id
```

### Assignment Configuration

Create JSON files in `backend/assignments/` for each project:

```json
{
  "id": "my-project",
  "name": "My Awesome Project",
  "description": "Customer-facing web application with microservices architecture",
  "status": "active",
  "start_date": "2024-01-15",
  "end_date": null,
  "monthly_burn_rate": 15000,
  "team_size": 5,
  "metrics_config": {
    "github": {
      "enabled": true,
      "org": "mycompany",
      "repos": ["web-app", "api-service", "worker-service"]
    },
    "jira": {
      "enabled": true,
      "project_key": "PROJ"
    },
    "aws": {
      "enabled": true,
      "account_id": "123456789012",
      "services": ["EC2", "S3", "RDS", "Route53"]
    },
    "railway": {
      "enabled": true,
      "project_id": "proj_abc123"
    }
  },
  "team": {
    "roles": ["Frontend Developer", "Backend Developer", "DevOps Engineer"],
    "tech_stack": ["React", "Python", "PostgreSQL", "AWS"]
  }
}
```

## 🎮 Usage

### Start the Application

1. **Start Backend Server:**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. **Start Frontend Development Server:**
```bash
cd frontend
npm run dev
```

3. **Access Dashboard:**
   - Open http://localhost:5173 in your browser
   - The backend API runs on http://localhost:8000

### Using the Dashboard

1. **View Assignment Overview:**
   - See all configured projects/assignments
   - Monitor team sizes, burn rates, and technology stacks
   - Check service integration status

2. **Explore Metrics:**
   - Click expandable sections for each service (GitHub, Jira, AWS, Railway)
   - View detailed metrics for repositories, issues, costs, and deployments

3. **Access CTO Insights:**
   - Click "View detailed CTO insights" in the AWS section
   - Review comprehensive cost analysis and trends
   - Examine resource inventory across all AWS services
   - Read strategic recommendations for cost optimization

4. **Monitor Costs:**
   - Track daily and weekly spending patterns
   - Identify top services by cost
   - Review resource utilization recommendations

## 📊 API Endpoints

### Core Endpoints
- `GET /` - Health check and API information
- `GET /health` - Service configuration status
- `GET /assignments` - List all assignments
- `GET /assignments/{id}` - Get specific assignment details
- `GET /assignments/{id}/metrics` - Get real-time metrics for an assignment
- `GET /assignments/{id}/cto-insights` - Get comprehensive CTO analysis

### Example API Response (CTO Insights)
```json
{
  "timestamp": "2024-08-28T18:16:57.845836",
  "cost_analysis": {
    "total_cost_30_days": 9.33,
    "daily_average": 0.31,
    "weekly_trend": "decreasing",
    "service_breakdown": {
      "Amazon Virtual Private Cloud": 3.24,
      "Amazon Lightsail": 3.235,
      "Amazon Route 53": 2.013516
    },
    "daily_costs": [...],
    "period": "2025-07-29 to 2025-08-28"
  },
  "route53_resources": {
    "total_hosted_zones": 3,
    "hosted_zones": [...],
    "suggestions": [...]
  },
  "s3_resources": {
    "total_buckets": 20,
    "buckets": [...],
    "total_size_readable": "1.9 GB"
  },
  "recommendations": [...],
  "assignment_info": {...}
}
```

## 🔒 Security

### API Key Management
- All sensitive API keys are stored in `.env` files (excluded from Git)
- Use environment variables for all external service credentials
- Follow least-privilege access principles for AWS IAM roles

### CORS Configuration
- Frontend origin is explicitly configured in backend CORS settings
- Credentials and headers are properly restricted

### Best Practices
- Never commit API keys or sensitive data to version control
- Use different `.env` files for development, staging, and production
- Implement API rate limiting and request validation

## 🚀 Deployment

### Development
```bash
# Backend
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend  
cd frontend && npm run dev
```

### Production Build
```bash
# Frontend production build
cd frontend && npm run build

# Backend production
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🔧 Development

### Adding New Metrics Services

1. **Create Service Module:**
```python
# backend/metrics_service.py
class NewServiceMetrics:
    def __init__(self):
        self.api_token = os.getenv("NEW_SERVICE_TOKEN")
    
    async def get_metrics(self, config):
        # Implementation here
        return metrics_data
```

2. **Update Metrics Aggregator:**
```python
# Add to MetricsAggregator.get_all_metrics()
if assignment_config.get("new_service", {}).get("enabled"):
    new_service = NewServiceMetrics()
    metrics["new_service"] = await new_service.get_metrics(config)
```

3. **Update Frontend:**
```tsx
// Add new service display in App.tsx
{assignmentMetrics.new_service && (
  <div className="metrics-section">
    {/* Display new service metrics */}
  </div>
)}
```

## 📈 Key Features Implemented

### ✅ Comprehensive AWS CTO Insights
- **Cost Analysis Dashboard** with 30-day trends and daily breakdowns
- **Resource Inventory** displaying EC2, Route53, S3, RDS, and Lightsail resources
- **Strategic Recommendations** with CTO-level actionable insights
- **Visual Cost Trends** with interactive charts and service breakdowns
- **Optimization Suggestions** with potential cost savings analysis

### ✅ Multi-Platform Integration
- **GitHub Metrics**: Repository activity, commits, PRs, and issues
- **Jira Integration**: Project tracking, resolution rates, and team productivity
- **AWS Cost Tracking**: Real-time cost monitoring and resource analysis
- **Railway Deployments**: Deployment success rates and project metrics

### ✅ Executive-Level Visibility
- **Assignment-based organization** for project-centric view
- **Team and technology stack** tracking
- **Monthly burn rate** monitoring and budget analysis
- **Service integration status** and health monitoring

### ✅ Technical Excellence
- **React + TypeScript** frontend with modern UI/UX
- **FastAPI backend** with async performance
- **CORS-enabled** secure API communication
- **Responsive design** with Tailwind CSS
- **Error handling** and loading states
- **Real-time data** from all integrated services

## 🆘 Troubleshooting

### Common Issues

**CORS Errors:**
```
Solution: Check FRONTEND_URL in backend/.env matches your frontend port (usually :5173)
```

**API Authentication Failures:**
```
Solution: Verify all API tokens in .env file are valid and have necessary permissions
```

**Missing Dependencies:**
```
Solution: Run `pip install -r requirements.txt` and `npm install` in respective directories
```

**AWS Cost Data Not Loading:**
```
Solution: Ensure AWS credentials have Cost Explorer read permissions
```

### Debug Mode
Enable detailed logging by setting environment variable:
```bash
export DEBUG=true
python -m uvicorn main:app --reload --log-level debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- **Python**: Follow PEP 8 standards
- **TypeScript**: Use ESLint and Prettier configurations
- **Documentation**: Update README.md for new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review API documentation and examples

---

**Built with ❤️ for executive visibility and data-driven decision making**
