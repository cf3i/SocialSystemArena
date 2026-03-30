import json
import urllib.request
import urllib.error
import sys
from pathlib import Path

def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)

def make_api_request(config):
    """Make HTTP request to API endpoint."""
    api_config = config.get('api', {})
    endpoint = api_config.get('endpoint', '')
    method = api_config.get('method', 'GET')
    headers = api_config.get('headers', {})
    timeout = api_config.get('timeout', 30)
    
    if not endpoint:
        print("Error: No API endpoint configured.")
        sys.exit(1)
    
    print(f"Making {method} request to: {endpoint}")
    
    try:
        req = urllib.request.Request(endpoint, method=method)
        for key, value in headers.items():
            req.add_header(key, value)
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.status
            body = response.read().decode('utf-8')
            
            print(f"Status: {status_code}")
            print(f"Response: {body}")
            return status_code, body
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    config = load_config()
    project_info = config.get('project', {})
    print(f"Project: {project_info.get('name', 'Unknown')} v{project_info.get('version', '?')}")
    print("-" * 50)
    make_api_request(config)

if __name__ == "__main__":
    main()