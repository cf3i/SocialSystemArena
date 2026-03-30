#!/usr/bin/env python3
"""
DataFetcher - Automated data fetching utility
Version: 1.0.0
"""

import json
import os
import sys
import requests

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r') as f:
        return json.load(f)

def fetch_data(config):
    api = config.get('api', {})
    endpoint = api.get('endpoint')
    method = api.get('method', 'GET')
    headers = api.get('headers', {})
    timeout = api.get('timeout', 30)
    
    print(f"Calling API: {method} {endpoint}")
    print(f"Timeout: {timeout}s")
    
    try:
        if method.upper() == 'GET':
            response = requests.get(endpoint, headers=headers, timeout=timeout)
        elif method.upper() == 'POST':
            response = requests.post(endpoint, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Error: Request timeout", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Error: Connection failed", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

def main():
    config = load_config()
    print(f"Project: {config['project']['name']} v{config['project']['version']}")
    print("-" * 50)
    data = fetch_data(config)
    if data:
        print("API Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("Failed to fetch data.")
        sys.exit(1)

if __name__ == "__main__":
    main()
