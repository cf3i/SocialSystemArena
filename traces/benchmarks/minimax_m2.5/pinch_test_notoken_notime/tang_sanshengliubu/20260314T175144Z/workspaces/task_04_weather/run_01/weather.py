#!/usr/bin/env python3
"""
Weather Script - Fetches weather data for San Francisco using wttr.in API
"""

import json
import urllib.request
import urllib.error


def get_weather():
    """Fetch weather data from wttr.in for San Francisco."""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        current = data.get('current_condition', [{}])[0]
        
        temp = current.get('temp_C', 'N/A')
        desc = current.get('weatherDesc', [{}])[0].get('value', 'N/A')
        humidity = current.get('humidity', 'N/A')
        wind = current.get('windspeedKmph', 'N/A')
        
        print(f"Weather Summary for San Francisco:")
        print(f"  Temperature: {temp}C")
        print(f"  Condition: {desc}")
        print(f"  Humidity: {humidity}%")
        print(f"  Wind Speed: {wind} km/h")
        
    except urllib.error.URLError as e:
        print(f"Error fetching weather data: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    get_weather()
