# Multi-step API Workflow - Notes

## Overview
This project implements an automated data fetching utility that reads API configuration from `config.json` and makes HTTP requests to the configured endpoint.

## Files Created

### 1. config.json
Configuration file containing API endpoint and project metadata.

**API Configuration:**
- **Endpoint:** `https://api.example.com/v2/data`
- **Method:** GET
- **Headers:**
  - Content-Type: application/json
  - Accept: application/json
- **Timeout:** 30 seconds

**Project Metadata:**
- **Name:** DataFetcher
- **Version:** 1.0.0
- **Description:** Automated data fetching utility

### 2. fetch_api.py
Python script that:
1. Reads and parses `config.json`
2. Extracts API endpoint and configuration
3. Makes HTTP GET request to the endpoint
4. Handles errors gracefully
5. Returns response status and body

## How to Use

```bash
python fetch_api.py
```

## Key Features

- Error handling for HTTP/URL errors and timeouts
- All settings from JSON config file
- Uses Python standard library only
