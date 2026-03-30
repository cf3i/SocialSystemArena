# API Client Notes

## Overview
This document describes the Python script `api_client.py` which makes HTTP requests to the API endpoint configured in `config.json`.

## What Was Done
1. Read `config.json` to extract API configuration
2. Created Python script `api_client.py` that:
   - Loads configuration from JSON file
   - Makes HTTP GET/POST requests to the configured endpoint
   - Handles errors gracefully (HTTP errors, URL errors, JSON parsing)
   - Prints response status and content

## Configuration
The script reads from `config.json` which contains:
- `api.endpoint`: The URL to call (e.g., https://api.example.com/v2/data)
- `api.method`: HTTP method (default: GET)
- `api.headers`: Request headers
- `api.timeout`: Request timeout in seconds (default: 30)

## How to Use

### Run the script:
```bash
python api_client.py
```

### Expected Output:
- Project name and version from config
- API response status code
- Response body (JSON formatted if applicable)

## Error Handling
The script handles:
- Missing config file
- Invalid JSON syntax
- HTTP errors (4xx, 5xx)
- Network errors
- Timeout errors

## Important Details
- Script location: Same directory as config.json
- Uses Python standard library (urllib)
- No external dependencies required