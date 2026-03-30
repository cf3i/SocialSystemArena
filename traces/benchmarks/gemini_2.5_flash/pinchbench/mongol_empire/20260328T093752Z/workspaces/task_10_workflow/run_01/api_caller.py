
import json
import requests
import sys
import os

def call_api_from_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        api_endpoint = config_data.get("api_endpoint")

        if not api_endpoint:
            print("Error: 'api_endpoint' not found in config.json.", file=sys.stderr)
            return None

        print(f"Calling API endpoint: {api_endpoint}")
        response = requests.get(api_endpoint)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        print("API call successful!")
        print("Response Status Code:", response.status_code)
        print("Response Body:")
        try:
            json_response = response.json()
            print(json.dumps(json_response, indent=2))
            return json_response
        except json.JSONDecodeError:
            print("Response is not valid JSON:", response.text)
            return response.text

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_path}", file=sys.stderr)
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}", file=sys.stderr)
        return None
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected request error occurred: {req_err}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to config.json relative to the script
    config_file_name = "config.json"
    config_file_path_for_script = os.path.join(script_dir, config_file_name)

    call_api_from_config(config_file_path_for_script)
