
import json
import requests
import os

CONFIG_FILE = "config.json"

def run_api_workflow():
    config_path = os.path.join(os.getcwd(), CONFIG_FILE)
    
    # 1. Read config.json
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: {CONFIG_FILE} not found at {config_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {CONFIG_FILE}")
        return

    # 2. Extract API endpoint
    api_endpoint = config.get("api", {}).get("endpoint")
    if not api_endpoint:
        print(f"Error: 'api.endpoint' not found in {CONFIG_FILE}")
        return

    api_method = config.get("api", {}).get("method", "GET").upper()
    api_headers = config.get("api", {}).get("headers", {})
    api_timeout = config.get("api", {}).get("timeout", 30)

    print(f"Attempting to call API: {api_method} {api_endpoint}")

    # 3. Make HTTP request with error handling
    try:
        if api_method == "GET":
            response = requests.get(api_endpoint, headers=api_headers, timeout=api_timeout)
        elif api_method == "POST":
            # Assuming no body for this simple task, but can be extended
            response = requests.post(api_endpoint, headers=api_headers, timeout=api_timeout)
        else:
            print(f"Error: Unsupported API method '{api_method}'")
            return

        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        print("API call successful!")
        print("Response Status Code:", response.status_code)
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print(response.text)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Status Code: {response.status_code}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected request error occurred: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_api_workflow()
