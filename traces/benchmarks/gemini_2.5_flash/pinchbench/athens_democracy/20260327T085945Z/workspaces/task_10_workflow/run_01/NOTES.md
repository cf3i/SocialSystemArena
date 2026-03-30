# Task 10: Multi-step API Workflow Documentation

## Objective
The goal of this task was to read an API endpoint from `config.json`, create a Python script `api_caller.py` to call this API, and document the process and outcomes in `NOTES.md`.

## `config.json`
The `config.json` file was successfully read to extract the API endpoint.
```json
{
  "api": {
    "endpoint": "https://api.example.com/v2/data"
  }
}
```
The identified API endpoint is `https://api.example.com/v2/data`.

## `api_caller.py`
The `api_caller.py` script was created to perform the API call. It includes basic error handling for network issues and JSON parsing.

**Script Content:**
```python
import requests
import json
import os

def call_api_from_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        api_endpoint = config.get('api', {}).get('endpoint')
        
        if not api_endpoint:
            print("Error: 'api_endpoint' not found in config.json under 'api.endpoint'.")
            return

        print(f"Calling API endpoint: {api_endpoint}")

        # Make a GET request to the API endpoint
        response = requests.get(api_endpoint, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        data = response.json()
        print("API call successful. Response data:")
        print(json.dumps(data, indent=2))

    except FileNotFoundError:
        print(f"Error: config.json not found at {config_path}")
    except json.JSONDecodeError:
        print("Error: Could not decode config.json. Please ensure it's valid JSON.")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error occurred: {e}")
    except requests.exceptions.Timeout:
        print("The request timed out.")
    except requests.exceptions.RequestException as e:
        print(f"An unexpected request error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    call_api_from_config()
```

## Execution Outcome
Upon executing `api_caller.py`, the script correctly read the `api_endpoint` from `config.json`. As `https://api.example.com` is a placeholder domain and not a real, resolvable server, the API call resulted in a `NameResolutionError`. This behavior is expected and demonstrates that the script correctly attempts to connect to the specified endpoint and handles the resulting connection error.

**Console Output:**
```
Calling API endpoint: https://api.example.com/v2/data
Connection error occurred: HTTPSConnectionPool(host='api.example.com', port=443): Max retries exceeded with url: /v2/data (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x...> : Failed to resolve 'api.example.com' ([Errno -3] Temporary failure in name resolution)"))
```

## Deliverables
- `config.json` (provided by the task)
- `api_caller.py`
- `NOTES.md`