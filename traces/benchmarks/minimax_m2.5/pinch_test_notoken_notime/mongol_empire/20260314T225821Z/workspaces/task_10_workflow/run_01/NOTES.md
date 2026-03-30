# API Client Notes

## What
Python script that reads config.json and makes HTTP requests.

## How
1. load_config() reads endpoint, method, timeout from config.json
2. make_api_request() executes HTTP call
3. Returns JSON with status and data

## Use
```bash
python api_client.py
```

## Details
- Default method: GET
- Default timeout: 30 seconds
- Handles URLError exceptions
