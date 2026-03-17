# NOTES.md - Multi-step API Workflow

## What Was Done

This project implements a multi-step API workflow that:
1. Reads configuration from `config.json`
2. Extracts the API endpoint and settings
3. Makes an HTTP request to the configured endpoint
4. Handles errors appropriately

## How the Script Works

### Configuration (`config.json`)
- `api.endpoint`: The target API URL
- `api.method`: HTTP method (GET, POST, etc.)
- `api.headers`: Request headers
- `api.timeout`: Request timeout in seconds
- `project.name/version/description`: Project metadata

### Script (`api_client.py`)

**Functions:**
- `load_config()`: Reads and parses config.json
- `call_api()`: Makes HTTP request with error handling
- `main()`: Orchestrates the workflow

**Key Features:**
- JSON configuration reading
- HTTP GET/POST support
- Timeout handling
- Error handling with meaningful messages
- Configurable via config.json (no hardcoding)

## How to Use

1. Ensure `config.json` exists in the same directory
2. Run the script:
   ```bash
   python api_client.py
   ```
3. The script will:
   - Load configuration from config.json
   - Extract the API endpoint
   - Make the HTTP request
   - Print the response status and body

## Important Details

- Requires `requests` library: `pip install requests`
- Default timeout is 30 seconds (configurable in config.json)
- API endpoint must be accessible from the running environment
- Content-Type header is set to application/json
