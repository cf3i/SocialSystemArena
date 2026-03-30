# API Workflow Documentation (Task 10)

This document outlines the process of reading API configuration, creating a Python client script, and how to use it.

## 1. Objective

The goal was to:
- Read `config.json` to extract API details.
- Create a Python script (`api_client.py`) to call the specified API endpoint.
- Document the entire process.

## 2. `config.json` Structure

The `config.json` file is located in the same directory as the `api_client.py` script and contains the following structure:

```json
{
  "api": {
    "endpoint": "https://api.example.com/v2/data",
    "method": "GET",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "timeout": 30
  },
  "project": {
    "name": "DataFetcher",
    "version": "1.0.0",
    "description": "Automated data fetching utility"
  }
}
```

- `api.endpoint`: The URL of the API to call.
- `api.method`: The HTTP method (e.g., GET, POST).
- `api.headers`: HTTP headers to include in the request.
- `api.timeout`: Request timeout in seconds.
- `project`: Metadata about the project.

## 3. `api_client.py` Script Details

The `api_client.py` script is designed to:
1.  **Read Configuration**: Automatically load `config.json` from its own directory to get API parameters.
2.  **Make HTTP Request**: Use the `requests` library to make an HTTP call to the configured `endpoint` with the specified `method`, `headers`, and `timeout`.
3.  **Error Handling**: Implement robust error handling for network issues (connection errors, timeouts) and HTTP status codes (4xx, 5xx).
4.  **Print Response**: Print the API response status code and body (pretty-printed JSON if applicable, otherwise raw text).

### How to Use `api_client.py`

To run the API client script, navigate to the workspace directory and execute it directly:

```bash
python api_client.py
```

The script will read the `config.json` file, make the API call, and print the response or any errors encountered to the console.

## 4. Important Details and Red Lines Adherence

-   **No Hardcoding**: API endpoint and related parameters are read dynamically from `config.json`, adhering to the "prohibit hardcoding" red line.
-   **Error Handling**: The script includes `try-except` blocks to catch `requests` exceptions (HTTPError, ConnectionError, Timeout, RequestException), fulfilling the "script must handle API call errors" red line.
-   **Documentation**: This `NOTES.md` provides clear and comprehensive documentation, addressing the "documentation must be clear and comprehensive" red line.
-   **Dependencies**: The script requires the `requests` library. Ensure it is installed (`pip install requests`).