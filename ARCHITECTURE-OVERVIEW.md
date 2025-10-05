# CTO Dashboard - Current Architecture Overview

## 🏗️ **Platform Architecture**

The CTO Dashboard is a comprehensive executive monitoring platform with a modern, scalable architecture that integrates multiple services and provides AI-powered insights.

## 📊 **High-Level Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CTO DASHBOARD PLATFORM                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐           │
│  │   Frontend      │    │   Backend API    │    │  External APIs  │           │
│  │   React/Vite    │◄──►│   Flask/Python   │◄──►│  GitHub, Jira   │           │
│  │   TypeScript    │    │   Async/Await    │    │  AWS, Railway   │           │
│  │   Tailwind CSS  │    │   CORS Enabled   │    │                 │           │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘           │
│           │                       │                       │                   │
│           │                       │                       │                   │
│           ▼                       ▼                       ▼                   │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐           │
│  │   Chatbot UI    │    │   Chatbot        │    │  MCP Server     │           │
│  │   (Modal)       │◄──►│   Service        │◄──►│  (AI Interface) │           │
│  │   Floating Btn  │    │   (Rule-based)   │    │                 │           │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 **Core Components**

### 1. **Frontend Layer (React + TypeScript)**
- **Location**: `frontend/`
- **Technology**: React 18, TypeScript, Vite, Tailwind CSS
- **Components**:
  - `App.tsx` - Main dashboard interface
  - `Chatbot.tsx` - AI chatbot modal interface
  - `ChatbotButton.tsx` - Floating action button
  - `CTOInsightsSection.tsx` - Detailed AWS insights
  - `LoadingSpinner.tsx` - Loading states

### 2. **Backend API Layer (Flask + Python)**
- **Location**: `backend/`
- **Technology**: Flask, Python 3.8+, Async/Await
- **Services**:
  - `main.py` - Flask application with API routes
  - `assignment_service.py` - Assignment management
  - `metrics_service.py` - Metrics aggregation
  - `chatbot_service.py` - AI chatbot logic

### 3. **Data Layer (JSON + External APIs)**
- **Assignment Storage**: JSON files in `backend/assignments/`
- **External Integrations**:
  - GitHub API v4 (GraphQL)
  - Jira REST API v3
  - AWS Boto3 (Cost Explorer, EC2, S3, Route53, RDS, Lightsail)
  - Railway API

### 4. **AI Layer (MCP + Chatbot)**
- **MCP Server**: `mcp_server.py` - Model Context Protocol server
- **Chatbot Service**: Rule-based AI with conversation history
- **Integration**: Direct access to all dashboard services

## 🔧 **Service Architecture**

### **Assignment Service**
```python
class AssignmentService:
    - get_all_assignments()
    - get_assignment(id)
    - create_assignment()
    - update_assignment()
    - archive_assignment()
```

### **Metrics Service**
```python
class MetricsAggregator:
    - get_all_metrics(assignment_config)
    
class GitHubMetrics:
    - get_repo_metrics(repo, org)
    
class JiraMetrics:
    - get_project_metrics(project_key)
    
class AWSMetrics:
    - get_comprehensive_aws_report()
    - get_cost_metrics()
    
class RailwayMetrics:
    - get_deployment_metrics()
```

### **Chatbot Service**
```python
class ChatbotService:
    - process_question(question, user_id)
    - get_conversation_history(user_id)
    - clear_conversation_history(user_id)
```

## 🌐 **API Endpoints**

### **Core API Routes**
- `GET /api` - API health check
- `GET /api/health` - Service status
- `GET /api/assignments` - List all assignments
- `GET /api/assignments/{id}` - Get specific assignment
- `GET /api/assignments/{id}/metrics` - Get assignment metrics
- `GET /api/assignments/{id}/cto-insights` - Get CTO insights

### **Chatbot API Routes**
- `POST /api/chatbot/ask` - Ask chatbot a question
- `GET /api/chatbot/history` - Get conversation history
- `POST /api/chatbot/clear` - Clear conversation history

## 📁 **Project Structure**

```
ctodashboard/
├── frontend/                    # React Frontend
│   ├── src/
│   │   ├── components/         # UI Components
│   │   │   ├── App.tsx
│   │   │   ├── Chatbot.tsx
│   │   │   ├── ChatbotButton.tsx
│   │   │   ├── CTOInsightsSection.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   ├── index.tsx
│   │   └── App.css
│   ├── dist/                   # Built React app
│   ├── package.json
│   └── vite.config.ts
├── backend/                     # Flask Backend
│   ├── main.py                 # Flask application
│   ├── assignment_service.py   # Assignment management
│   ├── metrics_service.py      # Metrics aggregation
│   ├── chatbot_service.py      # AI chatbot
│   ├── assignments/            # JSON data storage
│   │   ├── ideptech.json
│   │   ├── ilsainteractive.json
│   │   └── archived/
│   └── requirements.txt
├── ewm_skippy/                 # AI Coach System
│   ├── src/
│   │   ├── base_coach.py
│   │   ├── ewm_coach.py
│   │   ├── business_analyst_coach.py
│   │   ├── dev_guru_coach.py
│   │   └── support_coach.py
│   ├── data/                   # Vector databases
│   └── chroma/                 # ChromaDB storage
├── mcp_server.py               # MCP Server
├── mcp_client_example.py       # MCP Client
├── test_chatbot.py             # Chatbot testing
└── venv/                       # Python virtual environment
```

## 🔄 **Data Flow**

### **1. User Interaction Flow**
```
User → React Frontend → Flask API → Service Layer → External APIs
  ↑                                                      ↓
  └── Response ← JSON ← Processed Data ← Raw API Data ←──┘
```

### **2. Chatbot Flow**
```
User Question → Chatbot UI → Flask API → Chatbot Service → Data Analysis → AI Response
```

### **3. MCP Integration Flow**
```
AI Assistant → MCP Server → Dashboard Services → External APIs → Response
```

## 🚀 **Deployment Architecture**

### **Current Setup**
- **Frontend**: Built React app served by Flask
- **Backend**: Flask application with async support
- **Database**: JSON file storage (no database server needed)
- **External APIs**: Direct integration with service APIs

### **Deployment Options**
- **Railway**: `railway.json` configuration
- **Render**: `render.yaml` configuration
- **Vercel**: `vercel.json` configuration
- **Local**: Python virtual environment

## 🔐 **Security & Configuration**

### **Environment Variables**
```env
# GitHub
GITHUB_TOKEN=your_token
GITHUB_ORG=your_org

# Jira
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your_email
JIRA_TOKEN=your_token
JIRA_PROJECT_KEY=YOUR_PROJECT

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Railway
RAILWAY_TOKEN=your_token
RAILWAY_PROJECT_ID=your_project_id
```

### **Security Features**
- CORS enabled for cross-origin requests
- Environment variable configuration
- Input validation and error handling
- No sensitive data in code

## 📊 **Monitoring & Health Checks**

### **Health Endpoints**
- `GET /api/health` - Overall system health
- Service configuration status
- External API connectivity
- Error logging and monitoring

### **Metrics Tracking**
- Assignment metrics
- Cost analysis
- Service performance
- User engagement (chatbot)

## 🔮 **Future Architecture Considerations**

### **Scalability**
- Database migration (SQLite → PostgreSQL)
- Caching layer (Redis)
- Load balancing
- Microservices architecture

### **AI Enhancement**
- LLM integration (OpenAI, Claude)
- Vector database for semantic search
- Advanced conversation management
- Predictive analytics

### **Integration Expansion**
- Slack/Teams integration
- Email notifications
- Webhook support
- API rate limiting

## 🎯 **Key Architectural Decisions**

1. **Flask over FastAPI**: Chosen for simplicity and existing codebase
2. **JSON over Database**: Lightweight storage for MVP
3. **React over Vue**: TypeScript support and ecosystem
4. **Tailwind over Custom CSS**: Rapid development and consistency
5. **MCP Protocol**: Standardized AI integration
6. **Rule-based Chatbot**: Extensible to LLM integration

## 📈 **Performance Characteristics**

- **Response Time**: < 2 seconds for most operations
- **Concurrent Users**: Supports multiple users
- **Memory Usage**: Minimal footprint
- **Cost**: < $0.05/month operating cost
- **Scalability**: Horizontal scaling ready

This architecture provides a solid foundation for executive-level monitoring while maintaining simplicity and cost-effectiveness.

