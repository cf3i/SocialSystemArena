#!/usr/bin/env python3
"""
Weather script for San Francisco using wttr.in API
"""

import json
import urllib.request
import urllib.error
from urllib.request import Request


def get_weather():
    """
    Fetch and display weather data for San Francisco.
    Uses wttr.in API with JSON format.
    """
    url = "https://wttr.in/San_Francisco?format=j1"
    
    # Create request with User-Agent to avoid 403
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        # Make HTTP request with timeout
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Extract current weather information
        current = data['current_condition'][0]
        temp_c = current['temp_C']
        temp_f = current['temp_F']
        desc = current['weatherDesc'][0]['value']
        humidity = current['humidity']
        wind_speed = current['windspeedKmph']
        
        # Print formatted summary
        print("=" * 40)
        print("Weather Report for San Francisco")
        print("=" * 40)
        print(f"Condition: {desc}")
        print(f"Temperature: {temp_c}°C / {temp_f}°F")
        print(f"Humidity: {humidity}%")
        print(f"Wind Speed: {wind_speed} km/h")
        print("=" * 40)
        
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}")
    except json.JSONDecodeError:
        print("Error: Unable to parse weather data")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    get_weather()
