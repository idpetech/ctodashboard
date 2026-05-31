#!/usr/bin/env python3
"""
Debug GitHub token validation
"""
import requests
import sys
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def debug_github_validation(token):
    """Debug GitHub credentials with detailed logging"""
    logger.info("🔍 Testing GitHub token validation")
    logger.info(f"Token format: {'ghp_' if token.startswith('ghp_') else 'classic' if not token.startswith('ghp_') and len(token) == 40 else 'unknown'}")
    logger.info(f"Token length: {len(token)}")
    logger.info(f"Token prefix: {token[:8]}...")
    
    try:
        headers = {
            "Authorization": f"token {token}", 
            "User-Agent": "CTO-Dashboard",
            "Accept": "application/vnd.github.v3+json"
        }
        logger.info(f"Headers: {dict(headers)}")
        
        logger.info("Making request to GitHub API...")
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Success! User: {user_data.get('login')}")
            scopes = response.headers.get("x-oauth-scopes", "")
            logger.info(f"Token scopes: {scopes}")
            return {
                "valid": True,
                "user": user_data.get("login"),
                "name": user_data.get("name"),
                "scopes": scopes.split(", ") if scopes else []
            }
        elif response.status_code == 401:
            logger.error("❌ Token is invalid or expired")
            logger.error(f"Response body: {response.text}")
            return {"valid": False, "error": "Invalid GitHub token or expired"}
        elif response.status_code == 403:
            logger.error("❌ Token lacks required permissions")
            logger.error(f"Response body: {response.text}")
            rate_limit = response.headers.get("x-ratelimit-remaining")
            if rate_limit == "0":
                logger.error("Rate limit exceeded!")
            return {"valid": False, "error": "GitHub token lacks required permissions"}
        else:
            logger.error(f"❌ Unexpected status code: {response.status_code}")
            logger.error(f"Response body: {response.text}")
            return {"valid": False, "error": f"GitHub API error: {response.status_code}"}
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Connection error: {e}")
        return {"valid": False, "error": "Cannot connect to GitHub API - check internet connection"}
    except requests.exceptions.Timeout as e:
        logger.error(f"❌ Timeout error: {e}")
        return {"valid": False, "error": "GitHub API request timed out"}
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return {"valid": False, "error": f"GitHub connection failed: {str(e)}"}

if __name__ == "__main__":
    print("🔧 GitHub Token Debug Tool")
    print("This tool helps debug GitHub token validation issues")
    print()
    
    # Test with an obviously invalid token first
    print("Testing with invalid token...")
    result = debug_github_validation("invalid_token_for_testing")
    print(f"Result: {result}")
    print()
    
    print("To test your actual token, run:")
    print("python debug_github.py YOUR_TOKEN_HERE")
    
    if len(sys.argv) > 1:
        user_token = sys.argv[1]
        print("Testing your token...")
        result = debug_github_validation(user_token)
        print(f"Final result: {result}")