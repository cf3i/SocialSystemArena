import json
import requests
import os

# 读取config.json
workspace = "/home/feic/pjs/SocialSystemArena/traces/benchmarks/pinch_test_latest/soviet_party_state/20260315T003822Z/workspaces/task_10_workflow/run_01"
config_path = os.path.join(workspace, "config.json")

with open(config_path, 'r') as f:
    config = json.load(f)

# 提取API endpoint
api_config = config.get('api', {})
endpoint = api_config.get('endpoint', '')
method = api_config.get('method', 'GET')
headers = api_config.get('headers', {})
timeout = api_config.get('timeout', 30)

print(f"Calling {method} {endpoint}")
print(f"Headers: {headers}")
print(f"Timeout: {timeout}s")

# 发送HTTP请求
try:
    if method == 'GET':
        response = requests.get(endpoint, headers=headers, timeout=timeout)
    elif method == 'POST':
        response = requests.post(endpoint, headers=headers, timeout=timeout)
    else:
        print(f"Unsupported method: {method}")
        exit(1)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")