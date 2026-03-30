#!/usr/bin/env python3
"""
Weather script for San Francisco using wttr.in API
"""

import urllib.request
import urllib.error


def fetch_weather():
    """Fetch weather data for San Francisco from wttr.in"""
    url = "https://wttr.in/San_Francisco?format=3"
    
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            weather_data = response.read().decode('utf-8').strip()
            return weather_data
            
    except urllib.error.HTTPError as e:
        return f"Error: HTTP {e.code}"
    except urllib.error.URLError:
        return "Error: Network issue"
    except Exception as e:
        return f"Error: {str(e)}"


def main():
    """Main entry point"""
    print("Fetching San Francisco weather...")
    weather = fetch_weather()
    print(f"Weather: {weather}")


if __name__ == "__main__":
    main()
