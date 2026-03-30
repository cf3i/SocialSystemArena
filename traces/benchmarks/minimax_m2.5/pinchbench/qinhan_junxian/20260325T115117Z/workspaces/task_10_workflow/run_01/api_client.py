#!/usr/bin/env python3
"""
API Client Script
Reads config.json and makes HTTP request to the configured endpoint.
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Installing...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests


def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config


def extract_endpoint(config):
    """Extract API endpoint from config."""
    # Try various common keys
    for key in ["api_endpoint", "endpoint", "url", "api_url"]:
        if key in config:
            return config[key]
    raise ValueError("No API endpoint found in config")


def make_request(url, timeout=30):
    """Make HTTP GET request to the endpoint."""
    print(f"Making request to: {url}")
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out after {timeout} seconds")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {url}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def main():
    """Main execution function."""
    print("=== API Client Script ===")
    
    # Load config
    config = load_config()
    print(f"Config loaded: {list(config.keys())}")
    
    # Extract endpoint
    endpoint = extract_endpoint(config)
    print(f"Endpoint: {endpoint}")
    
    # Make request
    response = make_request(endpoint)
    
    if response:
        print(f"\n=== Response Status: {response.status_code} ===")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nResponse Body:")
        try:
            # Try to parse as JSON
            data = response.json()
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            # Print as text
            print(response.text[:1000])
    else:
        print("\n=== Request failed ===")
        sys.exit(1)
    
    print("\n=== Execution completed successfully ===")


if __name__ == "__main__":
    main()
