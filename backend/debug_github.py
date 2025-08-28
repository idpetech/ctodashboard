#!/usr/bin/env python3

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print('Environment variables:')
print('GITHUB_TOKEN:', os.getenv('GITHUB_TOKEN', 'NOT_SET')[:15] + '...')
print('GITHUB_ORG:', os.getenv('GITHUB_ORG', 'NOT_SET'))

# Test the API call with explicit debugging
token = os.getenv('GITHUB_TOKEN')
org = 'idpetech'
repo = 'idpetech_portal'
url = f'https://api.github.com/repos/{org}/{repo}'

print(f'Testing URL: {url}')
headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json'
}

print('Making request...')
response = requests.get(url, headers=headers)
print(f'Response status: {response.status_code}')

if response.status_code != 200:
    print(f'Response text: {response.text[:500]}')
    print(f'Response headers: {dict(response.headers)}')
else:
    print('Success! Repo found.')
    data = response.json()
    print(f'Repo name: {data.get("name")}')
    print(f'Language: {data.get("language")}')
    print(f'Stars: {data.get("stargazers_count")}')

# Also test the GitHubMetrics class
print('\n--- Testing GitHubMetrics class ---')
from metrics_service import GitHubMetrics
gh = GitHubMetrics()
print(f'GitHubMetrics token: {gh.token[:15]}... (length: {len(gh.token) if gh.token else 0})')
print(f'GitHubMetrics org: {gh.org}')

result = gh.get_repo_metrics('idpetech_portal', 'idpetech')
print(f'GitHubMetrics result: {result}')