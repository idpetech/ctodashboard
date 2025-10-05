# CTO Dashboard MCP Server Integration Guide

## Overview

The CTO Dashboard MCP (Model Context Protocol) server provides a standardized interface for AI assistants and external tools to interact with all dashboard services. This enables seamless integration with various AI platforms and automation tools.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Assistant  │    │   MCP Server     │    │  Dashboard      │
│   (Claude, etc) │◄──►│   (mcp_server.py)│◄──►│  Services       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   External       │
                       │   Tools/APIs     │
                       └──────────────────┘
```

## Services Exposed

### 1. Assignment Management
- **get_assignments**: Retrieve all assignments (with optional archived filter)
- **get_assignment**: Get specific assignment by ID
- **create_assignment**: Create new assignment
- **update_assignment**: Update existing assignment
- **archive_assignment**: Archive assignment

### 2. Metrics Aggregation
- **get_assignment_metrics**: Real-time metrics for specific assignment
- **get_github_metrics**: GitHub repository metrics
- **get_jira_metrics**: Jira project metrics
- **get_railway_metrics**: Railway deployment metrics
- **get_aws_insights**: Comprehensive AWS cost and resource insights

### 3. CTO Insights
- **get_cto_insights**: Detailed CTO-level insights for assignments
- **get_cost_optimization_recommendations**: AWS cost optimization recommendations

### 4. Health & Configuration
- **get_health_status**: Health status of all configured services
- **get_service_configuration**: Configuration status of all services

## Resources Available

- **assignments://active**: Active assignment configurations
- **assignments://archived**: Archived assignment configurations
- **assignments://all**: All assignment configurations
- **config://service-status**: Service configuration status
- **docs://api-endpoints**: API endpoints documentation

## Installation & Setup

### 1. Install Dependencies

```bash
# Install MCP-specific dependencies
pip install -r requirements-mcp.txt

# Or use the provided script
./run_mcp_server.sh
```

### 2. Environment Configuration

Ensure your `.env` file contains the necessary API tokens:

```env
# GitHub
GITHUB_TOKEN=your_github_token
GITHUB_ORG=your_org
GITHUB_API_URL=https://api.github.com

# Jira
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your_email@domain.com
JIRA_TOKEN=your_jira_token
JIRA_PROJECT_KEY=YOUR_PROJECT

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Railway
RAILWAY_TOKEN=your_railway_token
RAILWAY_PROJECT_ID=your_project_id
RAILWAY_API_URL=https://backboard.railway.app/graphql
```

### 3. Start the MCP Server

```bash
# Using the startup script
./run_mcp_server.sh

# Or manually
python3 mcp_server.py
```

## Usage Examples

### 1. Using with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "cto-dashboard": {
      "command": "python",
      "args": ["/path/to/ctodashboard/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/ctodashboard"
      }
    }
  }
}
```

### 2. Using with Python Client

```python
from mcp_client_example import CTODashboardMCPClient
import asyncio

async def main():
    client = CTODashboardMCPClient()
    
    # Connect to server
    await client.connect(["python", "mcp_server.py"])
    
    # Get all assignments
    assignments = await client.call_tool("get_assignments")
    print(assignments)
    
    # Get AWS insights
    aws_insights = await client.call_tool("get_aws_insights")
    print(aws_insights)
    
    # Disconnect
    await client.disconnect()

asyncio.run(main())
```

### 3. Interactive Mode

```bash
python3 mcp_client_example.py interactive
```

## Integration with Frontend

The MCP server complements the existing Flask API by providing:

1. **Standardized Interface**: Consistent tool and resource definitions
2. **AI Assistant Integration**: Direct integration with Claude, ChatGPT, etc.
3. **Automation Support**: Programmatic access to all dashboard functions
4. **Extensibility**: Easy to add new tools and resources

### Frontend Benefits

- **AI-Powered Insights**: AI assistants can analyze metrics and provide recommendations
- **Automated Reporting**: Generate reports using MCP tools
- **Smart Notifications**: AI can monitor metrics and alert on anomalies
- **Natural Language Queries**: Ask questions about assignments and metrics in natural language

## Tool Reference

### Assignment Management Tools

#### get_assignments
```json
{
  "include_archived": false
}
```

#### get_assignment
```json
{
  "assignment_id": "ideptech"
}
```

#### create_assignment
```json
{
  "assignment_data": {
    "id": "new-project",
    "name": "New Project",
    "status": "active",
    "start_date": "2024-01-01",
    "monthly_burn_rate": 1000,
    "team_size": 5,
    "description": "New project description",
    "metrics_config": {
      "github": {"enabled": true, "org": "myorg", "repos": ["repo1"]},
      "jira": {"enabled": true, "project_key": "PROJ"},
      "aws": {"enabled": true},
      "railway": {"enabled": false}
    },
    "team": {
      "roles": ["Developer", "Designer"],
      "tech_stack": ["React", "Node.js"]
    }
  }
}
```

### Metrics Tools

#### get_assignment_metrics
```json
{
  "assignment_id": "ideptech"
}
```

#### get_aws_insights
```json
{}
```

#### get_github_metrics
```json
{
  "repo": "my-repo",
  "org": "my-org"
}
```

## Error Handling

The MCP server includes comprehensive error handling:

- **Service Unavailable**: Graceful degradation when external services are down
- **Authentication Errors**: Clear error messages for missing or invalid tokens
- **Data Validation**: Input validation for all tool parameters
- **Logging**: Detailed logging for debugging and monitoring

## Security Considerations

1. **Environment Variables**: All sensitive data stored in environment variables
2. **Input Validation**: All inputs validated before processing
3. **Error Messages**: No sensitive information leaked in error messages
4. **Access Control**: Consider implementing authentication for production use

## Monitoring & Debugging

### Logging

The MCP server logs all operations:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Health Checks

Use the `get_health_status` tool to monitor service health:

```python
health = await client.call_tool("get_health_status")
```

### Service Configuration

Check service configuration status:

```python
config = await client.call_tool("get_service_configuration")
```

## Extending the MCP Server

### Adding New Tools

1. Add tool definition to `list_tools()`
2. Add handler to `call_tool()`
3. Update documentation

### Adding New Resources

1. Add resource definition to `list_resources()`
2. Add handler to `read_resource()`
3. Update documentation

### Example: Adding a New Tool

```python
# In list_tools()
Tool(
    name="get_custom_metrics",
    description="Get custom metrics for analysis",
    inputSchema=ToolInputSchema(
        type="object",
        properties={
            "metric_type": {
                "type": "string",
                "description": "Type of metrics to retrieve"
            }
        },
        required=["metric_type"]
    )
)

# In call_tool()
elif name == "get_custom_metrics":
    metric_type = arguments["metric_type"]
    # Your custom logic here
    result = get_custom_metrics(metric_type)
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    )
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Environment Variables**: Check that all required env vars are set
3. **Port Conflicts**: MCP server uses stdio, no port conflicts
4. **Permission Issues**: Ensure scripts have execute permissions

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Connection

Use the interactive client to test:

```bash
python3 mcp_client_example.py interactive
```

## Future Enhancements

1. **Authentication**: Add authentication for production use
2. **Rate Limiting**: Implement rate limiting for API calls
3. **Caching**: Add caching for frequently accessed data
4. **WebSocket Support**: Add real-time updates via WebSockets
5. **Batch Operations**: Support for batch tool calls
6. **Custom Prompts**: Add prompt templates for common queries

## Support

For issues or questions:

1. Check the logs for error messages
2. Verify environment configuration
3. Test with the interactive client
4. Review the API documentation resource

## License

This MCP server is part of the CTO Dashboard project and follows the same licensing terms.

