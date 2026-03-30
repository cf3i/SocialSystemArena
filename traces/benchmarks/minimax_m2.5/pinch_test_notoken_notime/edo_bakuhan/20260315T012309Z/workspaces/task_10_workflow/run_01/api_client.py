#!/usr/bin/env python3
"""
DataFetcher - Automated data fetching utility
Reads config.json and calls the API endpoint
"""
import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests")
    sys.exit(1)

def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def call_api(endpoint, method="GET", headers=None, timeout=30):
    """Make HTTP request to the API endpoint."""
    try:
        response = requests.request(method, endpoint, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return None

def main():
    # Load configuration
    config = load_config("config.json")
    
    api_config = config.get("api", {})
    endpoint = api_config.get("endpoint")
    method = api_config.get("method", "GET")
    headers = api_config.get("headers", {})
    timeout = api_config.get("timeout", 30)
    
    print(f"Calling API: {method} {endpoint}")
    
    # Make API call
    response = call_api(endpoint, method, headers, timeout)
    
    if response:
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    else:
        print("Failed to get response from API")

if __name__ == "__main__":
    main()
