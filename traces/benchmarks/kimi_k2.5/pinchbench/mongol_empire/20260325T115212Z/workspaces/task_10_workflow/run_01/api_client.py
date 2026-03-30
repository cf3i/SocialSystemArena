#!/usr/bin/env python3
"""
API Client Script - DataFetcher v1.0.0

Reads configuration from config.json and makes HTTP requests to the configured endpoint.
"""

import json
import sys
from pathlib import Path


def load_config(config_path="config.json"):
    """Load and parse the configuration file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)


def make_request(config):
    """Make HTTP request using configuration."""
    api_config = config.get('api', {})
    
    endpoint = api_config.get('endpoint')
    method = api_config.get('method', 'GET')
    headers = api_config.get('headers', {})
    timeout = api_config.get('timeout', 30)
    
    if not endpoint:
        print("Error: No endpoint configured in config.json")
        sys.exit(1)
    
    print(f"Making {method} request to: {endpoint}")
    print(f"Timeout: {timeout}s")
    print(f"Headers: {headers}")
    
    try:
        import requests
        
        response = requests.request(
            method=method,
            url=endpoint,
            headers=headers,
            timeout=timeout
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"\nResponse Body (JSON):\n{json.dumps(data, indent=2)}")
        except ValueError:
            print(f"\nResponse Body (Text):\n{response.text}")
            
        return response
        
    except ImportError:
        print("Error: 'requests' library not installed.")
        print("Install with: pip install requests")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out after {timeout} seconds")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"Error: Connection failed: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    
    print("=" * 50)
    print("DataFetcher API Client")
    print("=" * 50)
    
    config = load_config(config_path)
    
    project = config.get('project', {})
    print(f"\nProject: {project.get('name', 'Unknown')} v{project.get('version', '0.0.0')}")
    print(f"Description: {project.get('description', 'N/A')}\n")
    
    make_request(config)
    
    print("\n" + "=" * 50)
    print("Request completed")
    print("=" * 50)


if __name__ == "__main__":
    main()
