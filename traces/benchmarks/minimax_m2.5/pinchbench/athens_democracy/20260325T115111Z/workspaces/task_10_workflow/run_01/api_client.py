import json
import requests

# Read config.json
with open('config.json', 'r') as f:
    config = json.load(f)

# Extract API details
api_config = config['api']
endpoint = api_config['endpoint']
method = api_config['method']
headers = api_config.get('headers', {})
timeout = api_config.get('timeout', 30)

# Make HTTP request
try:
    if method == 'GET':
        response = requests.get(endpoint, headers=headers, timeout=timeout)
    elif method == 'POST':
        response = requests.post(endpoint, headers=headers, timeout=timeout)
    else:
        print(f"Unsupported method: {method}")
        exit(1)
    
    # Print response
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
    exit(1)