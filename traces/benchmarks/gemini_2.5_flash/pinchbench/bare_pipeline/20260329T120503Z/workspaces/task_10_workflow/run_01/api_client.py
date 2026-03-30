import json
import requests
import os

workspace_path = "/home/feic/pjs/SocialSystemArena/traces/benchmarks/gemini_2.5_flash/pinchbench/bare_pipeline/20260329T120503Z/workspaces/task_10_workflow/run_01"
config_file_path = os.path.join(workspace_path, "config.json")
output_file_path = os.path.join(workspace_path, "api_response.json")

def fetch_data():
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)

        api_config = config.get('api', {})
        endpoint = api_config.get('endpoint')
        method = api_config.get('method', 'GET')
        headers = api_config.get('headers', {})
        timeout = api_config.get('timeout', 30)

        if not endpoint:
            print("Error: API endpoint not found in config.json")
            return

        print(f"Attempting to call API: {endpoint} with method {method}")

        response = None
        if method.upper() == 'GET':
            response = requests.get(endpoint, headers=headers, timeout=timeout)
        elif method.upper() == 'POST':
            # Assuming no data for POST for now, as config.json only specifies GET
            response = requests.post(endpoint, headers=headers, timeout=timeout)
        else:
            print(f"Error: Unsupported HTTP method: {method}")
            return

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        json_response = response.json()
        print("API call successful!")
        print("Response:")
        print(json.dumps(json_response, indent=2))

        # Save response to a file
        with open(output_file_path, 'w') as outfile:
            json.dump(json_response, outfile, indent=2)
        print(f"API response saved to {output_file_path}")

    except FileNotFoundError:
        print(f"Error: config.json not found at {config_file_path}")
    except json.JSONDecodeError:
        print("Error: Could not decode config.json. Is it valid JSON?")
    except requests.exceptions.Timeout:
        print(f"Error: API request timed out after {timeout} seconds.")
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_data()