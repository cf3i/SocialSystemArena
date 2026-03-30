# API Workflow Notes

## Overview
This project implements an automated data fetching utility that reads API configuration from `config.json` and makes HTTP requests to the configured endpoint.

## What Was Done
1. Read `config.json` to extract API endpoint configuration
2. Created `fetch_data.py` Python script to make HTTP requests
3. Documented the workflow in this file

## How the Script Works

### Configuration (config.json)
- **endpoint**: `https://api.example.com/v2/data`
- **method**: GET
- **headers**: Content-Type: application/json, Accept: application/json
- **timeout**: 30 seconds

### Script Flow
1. `load_config()` - Reads and parses config.json
2. `fetch_data()` - Makes HTTP request using urllib
3. `main()` - Orchestrates the workflow and prints response

### Error Handling
- HTTP errors are caught and returned as error messages
- URL errors (connection issues) are handled gracefully
- Missing endpoint configuration raises ValueError

## How to Use

### Run the script:
```bash
python fetch_data.py
```

### Prerequisites:
- Python 3.x
- No external dependencies (uses standard library only)

## Important Details
- Project name: DataFetcher v1.0.0
- Description: Automated data fetching utility
- Uses Python's built-in urllib (no requests library needed)
