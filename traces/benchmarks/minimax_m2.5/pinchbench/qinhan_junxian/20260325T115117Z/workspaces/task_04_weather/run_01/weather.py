#!/usr/bin/env python3
"""
Weather script for San Francisco using wttr.in API
"""
import urllib.request
import json
import sys

def get_weather():
    """Fetch weather data from wttr.in API for San Francisco"""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Extract current weather information
        current = data.get('current_condition', [{}])[0]
        
        temp_f = current.get('temp_F', ['N/A'])[0]
        condition = current.get('weatherDesc', [{'value': 'N/A'}])[0].get('value', 'N/A')
        humidity = current.get('humidity', ['N/A'])[0]
        wind_speed = current.get('windspeedKmph', ['N/A'])[0]
        
        # Print weather summary
        print("=" * 40)
        print("San Francisco Weather Summary")
        print("=" * 40)
        print(f"Temperature: {temp_f}°F")
        print(f"Condition: {condition}")
        print(f"Humidity: {humidity}%")
        print(f"Wind Speed: {wind_speed} km/h")
        print("=" * 40)
        
    except urllib.error.URLError as e:
        print(f"Error fetching weather data: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing weather data: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    get_weather()
