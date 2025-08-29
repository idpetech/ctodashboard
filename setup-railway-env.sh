#!/bin/bash

# Railway Environment Variables Setup Script
# Run this after replacing the placeholder values with your actual API tokens

echo "Setting up Railway environment variables..."

# Set basic configuration
railway variables --set "FRONTEND_URL=*" --skip-deploys

# GitHub API Configuration
# Get your token from: https://github.com/settings/tokens
railway variables --set "GITHUB_TOKEN=your_github_token_here" --skip-deploys
railway variables --set "GITHUB_ORG=idpetech" --skip-deploys
railway variables --set "GITHUB_API_URL=https://api.github.com" --skip-deploys

# Jira API Configuration
# Get your token from Jira Account Settings > Security > API Tokens
railway variables --set "JIRA_URL=https://yourcompany.atlassian.net" --skip-deploys
railway variables --set "JIRA_EMAIL=your-email@company.com" --skip-deploys
railway variables --set "JIRA_TOKEN=your_jira_api_token" --skip-deploys

# AWS Configuration
railway variables --set "AWS_ACCESS_KEY_ID=your_aws_access_key" --skip-deploys
railway variables --set "AWS_SECRET_ACCESS_KEY=your_aws_secret_key" --skip-deploys
railway variables --set "AWS_REGION=us-east-1" --skip-deploys

# Railway API Configuration (optional - for self-monitoring)
railway variables --set "RAILWAY_TOKEN=your_railway_token" --skip-deploys
railway variables --set "RAILWAY_PROJECT_ID=your_railway_project_id" --skip-deploys
railway variables --set "RAILWAY_API_URL=https://backboard.railway.app/graphql" --skip-deploys

echo "Environment variables configured! Deploy with: railway up --detach"
