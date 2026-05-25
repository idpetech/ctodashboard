#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:3001}"
PASS=0; FAIL=0

check() {
  local name="$1" url="$2" jq_filter="${3:-.}"
  local body status
  body=$(curl -sS -w "\n%{http_code}" "$BASE$url")
  status=$(echo "$body" | tail -n1)
  body=$(echo "$body" | sed '$d')
  if [[ "$status" != "200" ]]; then
    echo "FAIL $name ($status) $url"; FAIL=$((FAIL+1)); return
  fi
  if ! echo "$body" | jq -e "$jq_filter" >/dev/null 2>&1; then
    echo "FAIL $name (jq) $url"; FAIL=$((FAIL+1)); return
  fi
  echo "PASS $name"; PASS=$((PASS+1))
}

check health           "/health"                          '.status'
check feature-flags    "/api/feature-flags"               '.multi_tenancy != null'
check assignments      "/api/assignments"                 'length >= 2'
check ideptech-metrics "/api/all-metrics/ideptech"        '.aws or .github or .jira'
check aws-metrics      "/api/aws-metrics"                 '. != null'
check github-metrics   "/api/github-metrics/ideptech"     '. != null'
check jira-metrics     "/api/jira-metrics/ideptech"       '. != null'

echo "---"
echo "PASS=$PASS FAIL=$FAIL"
[[ $FAIL -eq 0 ]]
