# API Workflow Notes

## Overview
This document records the multi-step API workflow task execution.

## What Was Done

1. **Read config.json**: Extracted API configuration including endpoint, method, headers, and timeout.

2. **Created api_client.py**: A Python script that:
   - Reads the config.json file
   - Parses the API configuration
   - Makes HTTP requests (GET/POST) to the endpoint
   - Handles errors appropriately
   - Prints response status and content

## Configuration Details

From config.json:
- **Endpoint**: https://api.example.com/v2/data
- **Method**: GET
- **Headers**: Content-Type: application/json, Accept: application/json
- **Timeout**: 30 seconds
- **Project**: DataFetcher v1.0.0

## How to Use the Script

```bash
python api_client.py
```

The script will:
1. Load configuration from config.json
2. Send an HTTP request to the configured endpoint
3. Print the response status code and body

## Error Handling

The script handles:
- File not found errors (missing config.json)
- Network errors (connection failures, timeouts)
- HTTP error responses (4xx, 5xx status codes)

## Important Notes

- Ensure config.json exists in the same directory as api_client.py
- The endpoint is a placeholder (api.example.com) - replace with actual API URL
- Modify headers as needed for your specific API requirements