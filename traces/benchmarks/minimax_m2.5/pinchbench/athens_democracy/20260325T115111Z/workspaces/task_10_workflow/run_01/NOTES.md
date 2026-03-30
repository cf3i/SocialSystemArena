# API Client Documentation

## Configuration
The script reads from `config.json`:
- `api.endpoint`: URL to call
- `api.method`: HTTP method (GET/POST)
- `api.headers`: Optional headers dict
- `api.timeout`: Request timeout in seconds (default: 30)

## Usage
```bash
python api_client.py
```

## Error Handling
- Network errors (DNS resolution, connection timeout) are caught and printed
- Unsupported HTTP methods trigger exit with error message
- Non-200 status codes are printed but don't crash (response still displayed)