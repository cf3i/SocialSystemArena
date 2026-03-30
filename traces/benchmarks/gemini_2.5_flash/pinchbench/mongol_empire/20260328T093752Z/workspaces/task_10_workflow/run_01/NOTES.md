# Multi-step API Workflow Documentation

This document outlines the process of reading a configuration file, extracting an API endpoint, and creating a Python script to call that endpoint with appropriate error handling.

## 1. What was done

1.  **`config.json` creation**: A `config.json` file was created in the workspace to store the API endpoint.
2.  **API Endpoint Extraction**: The `config.json` file was read and parsed to dynamically extract the API endpoint URL.
3.  **Python Script (`api_caller.py`) Generation**: A Python script named `api_caller.py` was created to perform the HTTP request to the extracted endpoint.
4.  **Documentation (`NOTES.md`)**: This `NOTES.md` file was created to document the entire workflow, script usage, and configuration details.

## 2. How the Script (`api_caller.py`) Works

The `api_caller.py` script performs the following actions:

*   **Reads `config.json`**: It opens and parses the `config.json` file located in the same directory as the script to retrieve the `api_endpoint` URL.
*   **Makes HTTP Request**: It uses the `requests` library to send a GET request to the specified API endpoint.
*   **Error Handling**: It includes comprehensive error handling for:
    *   `FileNotFoundError`: If `config.json` is missing.
    *   `json.JSONDecodeError`: If `config.json` is malformed.
    *   `requests.exceptions.HTTPError`: For HTTP status codes indicating an error (e.g., 404, 500).
    *   `requests.exceptions.ConnectionError`: For network-related issues (e.g., no internet connection).
    *   `requests.exceptions.Timeout`: If the API call times out.
    *   `requests.exceptions.RequestException`: A base exception for all `requests` library errors.
    *   General `Exception`: For any other unexpected errors.
*   **Response Handling**: If the API call is successful, it attempts to parse the response as JSON and prints it in a human-readable format. If the response is not JSON, it prints the raw text.
*   **Main Execution Block**: The script is designed to be run directly. When executed, it automatically calls the `call_api_from_config` function, passing the path to `config.json` relative to its own location.

## 3. How to Use the Script

1.  **Ensure `config.json` exists**: Make sure a `config.json` file is present in the same directory as `api_caller.py` with an `api_endpoint` key.
    ```json
    {
      "api_endpoint": "YOUR_API_ENDPOINT_HERE"
    }
    ```
2.  **Install dependencies**: The script uses the `requests` library. If you don't have it installed, run:
    ```bash
    pip install requests
    ```
3.  **Run the script**: Navigate to the directory containing `api_caller.py` and `config.json` in your terminal and execute:
    ```bash
    python api_caller.py
    ```
    The script will print the API response or any error messages to the console.

## 4. Important Configuration Details

*   **`config.json` location**: The `config.json` file must be in the same directory as `api_caller.py` for the script to find it automatically.
*   **`api_endpoint` key**: The API URL must be specified under the key `"api_endpoint"` in `config.json`.
*   **Error Reporting**: All errors are printed to `stderr` for better separation from successful output.
*   **Example Endpoint**: The provided `config.json` uses `https://jsonplaceholder.typicode.com/posts/1` as a placeholder for testing purposes. You should replace this with your actual API endpoint.
