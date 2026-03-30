# API Workflow Documentation

This document outlines the purpose, functionality, usage, and configuration details of the `api_workflow.py` script.

## 1. What was done

A Python script named `api_workflow.py` was created to automate the process of making HTTP requests to a specified API endpoint. The script's behavior, including the target API endpoint, HTTP method, headers, and timeout, is dynamically configured via a `config.json` file.

## 2. How the script works

The `api_workflow.py` script performs the following steps:

1.  **Reads Configuration**: It first reads the `config.json` file located in the same directory to retrieve API parameters.
2.  **Extracts API Details**: It extracts the `endpoint`, `method`, `headers`, and `timeout` from the `api` section of the `config.json`.
3.  **Makes HTTP Request**: Using the `requests` library, it constructs and sends an HTTP request (currently supporting GET and POST methods) to the specified `endpoint`.
4.  **Handles Responses**:
    *   If the API call is successful (HTTP status 2xx), it prints the status code and the JSON response body (if available).
    *   If the response is not JSON, it prints the raw text.
5.  **Error Handling**: The script includes robust error handling for various scenarios:
    *   `FileNotFoundError`: If `config.json` is missing.
    *   `json.JSONDecodeError`: If `config.json` is malformed.
    *   Missing `api.endpoint` in `config.json`.
    *   `requests.exceptions.HTTPError`: For 4xx or 5xx HTTP status codes.
    *   `requests.exceptions.ConnectionError`: For network connectivity issues.
    *   `requests.exceptions.Timeout`: If the request exceeds the specified timeout.
    *   General `requests.exceptions.RequestException` and other unexpected errors.

## 3. How to use it

To use the `api_workflow.py` script:

1.  **Prerequisites**:
    *   Ensure Python 3 is installed.
    *   Install the `requests` library: `pip install requests`
    *   Make sure a `config.json` file is present in the same directory as `api_workflow.py`.
2.  **Execution**:
    *   Run the script from your terminal: `python api_workflow.py`

## 4. Important details about the configuration (`config.json`)

The `config.json` file should follow this structure:

```json
{
  "api": {
    "endpoint": "YOUR_API_ENDPOINT_URL",
    "method": "GET", // or "POST"
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "timeout": 30 // in seconds
  },
  "project": {
    "name": "DataFetcher",
    "version": "1.0.0",
    "description": "Automated data fetching utility"
  }
}
```

*   **`api.endpoint`**: (Required) The full URL of the API you wish to call.
*   **`api.method`**: (Optional, defaults to "GET") The HTTP method to use (e.g., "GET", "POST").
*   **`api.headers`**: (Optional) A dictionary of HTTP headers to send with the request.
*   **`api.timeout`**: (Optional, defaults to 30) The maximum number of seconds to wait for a response.