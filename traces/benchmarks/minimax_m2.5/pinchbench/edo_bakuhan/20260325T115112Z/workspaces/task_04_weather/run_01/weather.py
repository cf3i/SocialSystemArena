#!/usr/bin/env python3
"""
Weather script to fetch San Francisco weather data from wttr.in
"""

import json
import urllib.request
import urllib.error

def get_weather(location="San_Francisco"):
    """Fetch weather data from wttr.in API"""
    url = f"https://wttr.in/{location}?format=j1"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except urllib.error.URLError as e:
        print(f"Error fetching weather data: {e}")
        return None
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def print_weather_summary(data):
    """Print a readable weather summary"""
    if not data or "current_condition" not in data:
        print("No weather data available")
        return
    
    current = data["current_condition"][0]
    location = data.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", "Unknown")
    
    print(f"=== Weather in {location} ===")
    print(f"Temperature: {current.get('temp_C', 'N/A')}°C ({current.get('temp_F', 'N/A')}°F)")
    print(f"Condition: {current.get('weatherDesc', [{}])[0].get('value', 'N/A')}")
    print(f"Humidity: {current.get('humidity', 'N/A')}%")
    print(f"Wind: {current.get('windspeedKmph', 'N/A')} km/h")
    print(f"Feels like: {current.get('FeelsLikeC', 'N/A')}°C")

def main():
    """Main function"""
    weather_data = get_weather("San_Francisco")
    print_weather_summary(weather_data)

if __name__ == "__main__":
    main()
