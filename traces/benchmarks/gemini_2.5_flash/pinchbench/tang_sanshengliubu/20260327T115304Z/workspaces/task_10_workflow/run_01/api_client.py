
import json
import requests
import os

def call_api():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: config.json not found at {config_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_path}")
        return None

    api_config = config.get("api", {})
    endpoint = api_config.get("endpoint")
    method = api_config.get("method", "GET")
    headers = api_config.get("headers", {})
    timeout = api_config.get("timeout", 30)

    if not endpoint:
        print("Error: API endpoint not found in config.json")
        return None

    print(f"Calling API: {method} {endpoint}")
    try:
        response = requests.request(method, endpoint, headers=headers, timeout=timeout)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        print("API call successful!")
        print("Response Status Code:", response.status_code)
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print(response.text)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred: {req_err}")
    return None

if __name__ == "__main__":
    call_api()
