# API Workflow Documentation

## Overview

This project demonstrates a multi-step workflow for reading configuration from `config.json` and making API calls using Python.

## What Was Done

1. **Configuration Analysis**: Read `config.json` to extract API endpoint details
2. **Script Development**: Created `api_client.py` with robust error handling
3. **Documentation**: This file explaining the process and usage

## Configuration Details

The `config.json` contains:

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

## How the Script Works

`api_client.py` performs these steps:

1. **Load Config**: Reads and parses `config.json`
2. **Extract Settings**: Gets endpoint, method, headers, timeout from the `api` section
3. **Make Request**: Uses `requests` library with proper error handling
4. **Output Response**: Displays status code, headers, and formatted JSON response

Error handling covers:
- Missing config file
- Invalid JSON syntax
- Missing endpoint configuration
- Network timeouts
- Connection failures
- HTTP request exceptions

## Usage

### Prerequisites

```bash
pip install requests
```

### Running the Script

```bash
python api_client.py
```

Or with explicit config path:

```bash
python api_client.py /path/to/config.json
```

## Project Information

- **Name**: DataFetcher
- **Version**: 1.0.0
- **Description**: Automated data fetching utility