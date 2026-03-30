#!/usr/bin/env python3
"""
DataFetcher - Automated data fetching utility
Reads config.json and makes HTTP requests to the configured API endpoint.
"""

import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def load_config(config_path: str = "config.json") -> dict:
    """Load and parse the configuration file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)


def make_api_request(config: dict) -> dict:
    """
    Make HTTP request to the API endpoint defined in config.
    """
    api_config = config.get('api', {})
    endpoint = api_config.get('endpoint', '')
    method = api_config.get('method', 'GET').upper()
    headers = api_config.get('headers', {})
    timeout = api_config.get('timeout', 30)
    
    if not endpoint:
        return {"error": "No API endpoint configured"}
    
    request = Request(endpoint, method=method)
    for key, value in headers.items():
        request.add_header(key, value)
    
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode('utf-8')
            return {
                "status": response.status,
                "body": body,
                "headers": dict(response.headers)
            }
    except HTTPError as e:
        return {"error": f"HTTP Error {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": f"URL Error: {e.reason}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def main():
    """Main entry point."""
    print("=" * 50)
    print("DataFetcher - API Data Fetching Utility")
    print("=" * 50)
    
    config = load_config()
    project_info = config.get('project', {})
    
    print(f"\nProject: {project_info.get('name', 'N/A')} v{project_info.get('version', 'N/A')}")
    print(f"Description: {project_info.get('description', 'N/A')}")
    
    api_config = config.get('api', {})
    print(f"\nAPI Endpoint: {api_config.get('endpoint', 'N/A')}")
    print(f"Method: {api_config.get('method', 'GET')}")
    print(f"Timeout: {api_config.get('timeout', 30)}s")
    
    print("\nMaking API request...")
    result = make_api_request(config)
    
    print("\n" + "-" * 50)
    print("Response:")
    print("-" * 50)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    else:
        print(f"Status: {result.get('status', 'N/A')}")
        body = result.get('body', 'N/A')
        print(f"Body: {body[:500]}...")
        return 0


if __name__ == "__main__":
    sys.exit(main())
