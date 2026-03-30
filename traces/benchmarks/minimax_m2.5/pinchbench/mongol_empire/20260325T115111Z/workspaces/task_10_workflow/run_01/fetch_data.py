#!/usr/bin/env python3
"""
DataFetcher - Automated data fetching utility
Reads config.json and makes HTTP request to the configured API endpoint.
"""
import json
import sys
try:
    import urllib.request
    import urllib.error
except ImportError:
    import urllib2 as urllib.request
    import urllib2 as urllib.error

def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)

def fetch_data(config):
    """Make HTTP request to API endpoint."""
    api_config = config.get("api", {})
    endpoint = api_config.get("endpoint", "")
    method = api_config.get("method", "GET")
    headers = api_config.get("headers", {})
    timeout = api_config.get("timeout", 30)
    
    if not endpoint:
        raise ValueError("No API endpoint configured")
    
    # Build request
    req = urllib.request.Request(endpoint, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    
    # Make request
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            return data.decode("utf-8")
    except urllib.error.HTTPError as e:
        return "HTTP Error: " + str(e.code) + " - " + str(e.reason)
    except urllib.error.URLError as e:
        return "URL Error: " + str(e.reason)

def main():
    config = load_config()
    result = fetch_data(config)
    print(result)
    return 0

if __name__ == "__main__":
    sys.exit(main())
