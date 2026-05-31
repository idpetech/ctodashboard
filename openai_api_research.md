# OpenAI API Usage & Billing Research

## 🔍 **Current OpenAI API Endpoints (2025)**

### **1. Usage API**
```
GET https://api.openai.com/v1/organization/usage?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```
- **Authentication**: Bearer token (API key)
- **Returns**: Usage data by date, model, and operation
- **Data**: Token counts, request counts, costs per model

### **2. Billing API** 
```
GET https://api.openai.com/v1/dashboard/billing/subscription
GET https://api.openai.com/v1/dashboard/billing/usage?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```
- **Authentication**: Bearer token
- **Returns**: Subscription details, credit grants, billing usage
- **Data**: Account balance, spending limits, usage by day/model

### **3. Projects API** (New)
```
GET https://api.openai.com/v1/organization/projects
GET https://api.openai.com/v1/organization/projects/{project_id}/usage
```
- **Authentication**: Bearer token  
- **Returns**: Project-specific usage and costs
- **Data**: Per-project breakdowns, team usage

## 📊 **Data Structure Examples**

### Usage Response:
```json
{
  "data": [
    {
      "timestamp": "2025-05-30",
      "model": "gpt-4",
      "n_requests": 150,
      "n_context_tokens_total": 45000,
      "n_generated_tokens_total": 15000,
      "cost": 1.35
    }
  ]
}
```

### Billing Response:
```json
{
  "account": {
    "balance": 25.50,
    "usage_limit": 100.00,
    "billing_email": "admin@company.com"
  },
  "grants": [
    {
      "amount": 5.00,
      "expires_at": "2025-06-30"
    }
  ]
}
```

## 🏗️ **Enhanced CTO Dashboard Integration**

### **Metrics to Track:**
1. **Monthly spending** by model (GPT-4, GPT-3.5, etc.)
2. **Token usage trends** (input vs output tokens)
3. **Request patterns** (daily/hourly usage)
4. **Cost per request** analysis
5. **Account balance** and remaining credits
6. **Project-specific** costs (if using projects)
7. **Rate limiting** and quota usage

### **CTO-Focused Insights:**
- **Cost efficiency**: Which models provide best ROI
- **Usage spikes**: Detect unexpected usage increases
- **Budget tracking**: Monthly spend vs budget goals
- **Optimization opportunities**: Identify expensive prompts
- **Team usage**: Who's using what (via projects)

### **Implementation Approach:**
1. **Real-time metrics**: Current month usage and costs
2. **Historical analysis**: 3-month trends and patterns  
3. **Budget alerts**: Configurable spending thresholds
4. **Cost forecasting**: Predict monthly spend based on usage
5. **Optimization suggestions**: Recommend cost-saving strategies

## 🔧 **Technical Implementation**

### **Authentication:**
- Use organization API keys (not project keys)
- Store securely in workspace credentials
- Handle rate limiting (3 requests/minute for billing API)

### **Data Refresh:**
- **Real-time**: Usage API every 15 minutes
- **Daily**: Billing API once per day  
- **Historical**: Cached for performance

### **Error Handling:**
- Handle 429 (rate limiting) with backoff
- Graceful degradation for API failures
- Clear error messages for invalid keys

## 💡 **Enhanced Features to Implement**

1. **Cost Prediction**: Forecast monthly spending based on current usage patterns
2. **Efficiency Metrics**: Cost per conversation, tokens per dollar
3. **Model Comparison**: ROI analysis for different OpenAI models
4. **Usage Anomaly Detection**: Alert on unusual spending spikes
5. **Team Analytics**: Track usage by team/project
6. **Optimization Recommendations**: Suggest prompt engineering improvements