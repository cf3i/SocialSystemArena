#!/usr/bin/env python3
"""
Weather script for San Francisco using wttr.in API
"""

import urllib.request
import urllib.error
import json
import sys


def fetch_weather():
    """
    Fetch weather data for San Francisco from wttr.in API
    """
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; WeatherScript/1.0)"
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Data Parse Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        return None


def parse_weather(data):
    """
    Parse weather data and extract key information
    """
    if not data or 'current_condition' not in data:
        return None
    
    current = data['current_condition'][0]
    location = data.get('nearest_area', [{}])[0]
    
    weather_info = {
        'location': f"{location.get('areaName', [{}])[0].get('value', 'San Francisco')}, "
                   f"{location.get('region', [{}])[0].get('value', 'CA')}",
        'temperature_f': current.get('temp_F', 'N/A'),
        'temperature_c': current.get('temp_C', 'N/A'),
        'condition': current.get('weatherDesc', [{}])[0].get('value', 'Unknown'),
        'humidity': current.get('humidity', 'N/A'),
        'wind': current.get('windspeedMiles', 'N/A'),
        'feels_like_f': current.get('FeelsLikeF', 'N/A'),
    }
    
    return weather_info


def print_summary(weather_info):
    """
    Print formatted weather summary
    """
    if not weather_info:
        print("Unable to retrieve weather information.")
        return
    
    print("=" * 50)
    print(f"  Weather Summary for {weather_info['location']}")
    print("=" * 50)
    print(f"  Condition:     {weather_info['condition']}")
    print(f"  Temperature:   {weather_info['temperature_f']}°F ({weather_info['temperature_c']}°C)")
    print(f"  Feels Like:    {weather_info['feels_like_f']}°F")
    print(f"  Humidity:      {weather_info['humidity']}%")
    print(f"  Wind Speed:    {weather_info['wind']} mph")
    print("=" * 50)


def main():
    """
    Main entry point
    """
    print("Fetching weather data for San Francisco...")
    
    data = fetch_weather()
    
    if data:
        weather_info = parse_weather(data)
        print_summary(weather_info)
    else:
        print("Failed to fetch weather data. Please check your network connection.")
        sys.exit(1)


if __name__ == "__main__":
    main()
