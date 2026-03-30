import requests
import json
import os

CONFIG_FILE = 'config.json'

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, CONFIG_FILE)
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{config_path}'. Check file format.")
        return None

def call_api(endpoint):
    try:
        print(f"Calling API endpoint: {endpoint}")
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        print("API Call Successful!")
        print("Response Status Code:", response.status_code)
        print("Response Body (first 500 chars):", response.text[:500])
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected request error occurred: {req_err}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from API response.")
    return None

if __name__ == "__main__":
    config = load_config()
    if config and 'api' in config and 'endpoint' in config['api']:
        api_endpoint = config['api']['endpoint']
        api_data = call_api(api_endpoint)
        if api_data:
            print("\nAPI Data received:")
            # For demonstration, print a snippet or specific keys
            # In a real scenario, you'd process this data further
            print(json.dumps(api_data, indent=2)[:1000]) # Print first 1000 chars of formatted JSON
    else:
        print("Failed to get API endpoint from configuration.")