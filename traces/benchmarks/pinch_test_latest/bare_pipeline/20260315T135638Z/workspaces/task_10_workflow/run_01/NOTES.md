#!/usr/bin/env python3
"""
DataFetcher - Automated data fetching utility
Reads config.json and makes HTTP requests to the configured API endpoint.
"""

import json
import sys
import os
import urllib.request
import urllib.error
import urllib.parse


def load_config(config_path: str) -> dict:
    """Load and parse the configuration file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)


def fetch_data(endpoint: str, method: str = "GET", headers: dict = None, timeout: int = 30) -> dict:
    """
    Make an HTTP request to the API endpoint.
    
    Args:
        endpoint: The API URL
        method: HTTP method (GET, POST, etc.)
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
    
    Returns:
        Response data as dictionary
    """
    if headers is None:
        headers = {}
    
    try:
        request = urllib.request.Request(endpoint, method=method, headers=headers)
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode('utf-8')
            return {
                'status_code': response.status,
                'body': response_body,
                'headers': dict(response.headers)
            }
    except urllib.error.HTTPError as e:
        return {
            'error': True,
            'status_code': e.code,
            'message': f"HTTP Error: {e.reason}",
            'body': e.read().decode('utf-8') if e.fp else None
        }
    except urllib.error.URLError as e:
        return {
            'error': True,
            'message': f"URL Error: {e.reason}"
        }
    except Exception as e:
        return {
            'error': True,
            'message': f"Unexpected error: {str(e)}"
        }


def main():
    """Main entry point."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    # Load configuration
    print("Loading configuration...")
    config = load_config(config_path)
    
    api_config = config.get('api', {})
    project_info = config.get('project', {})
    
    endpoint = api_config.get('endpoint')
    method = api_config.get('method', 'GET')
    headers = api_config.get('headers', {})
    timeout = api_config.get('timeout', 30)
    
    print(f"Project: {project_info.get('name')} v{project_info.get('version')}")
    print(f"Endpoint: {endpoint}")
    print(f"Method: {method}")
    print(f"Timeout: {timeout}s")
    print("-" * 50)
    
    # Make the API request
    print("Fetching data...")
    result = fetch_data(endpoint, method, headers, timeout)
    
    # Print results
    if result.get('error'):
        print(f"Error: {result.get('message')}")
        if 'status_code' in result:
            print(f"Status Code: {result.get('status_code')}")
        if result.get('body'):
            print(f"Response Body: {result.get('body')}")
        sys.exit(1)
    else:
        print(f"Success! Status Code: {result.get('status_code')}")
        print(f"Response: {result.get('body')}")
        return result


if __name__ == '__main__':
    main()