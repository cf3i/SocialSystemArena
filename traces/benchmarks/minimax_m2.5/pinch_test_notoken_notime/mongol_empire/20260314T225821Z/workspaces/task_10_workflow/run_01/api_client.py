
import json
import urllib.request
import urllib.error

def load_config(config_path="config.json"):
    with open(config_path, 'r') as f:
        return json.load(f)

def make_api_request(config):
    url = config.get('endpoint')
    method = config.get('method', 'GET')
    timeout = config.get('timeout', 30)
    
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return {
                'status': response.status,
                'data': response.read().decode('utf-8')
            }
    except urllib.error.URLError as e:
        return {'status': 'error', 'message': str(e)}

if __name__ == "__main__":
    config = load_config()
    result = make_api_request(config)
    print(json.dumps(result, indent=2))
