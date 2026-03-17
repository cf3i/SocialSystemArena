import urllib.request
import urllib.error
import json
import sys

def get_weather():
    """Fetch weather data for San Francisco from wttr.in API"""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Extract current weather info
        current = data.get('current_condition', [{}])[0]
        
        temp = current.get('temp_C', 'N/A')
        weather_desc = current.get('weatherDesc', [{}])[0].get('value', 'N/A')
        humidity = current.get('humidity', 'N/A')
        wind = current.get('windspeedKmph', 'N/A')
        
        print("=" * 40)
        print("Weather Summary - San Francisco")
        print("=" * 40)
        print(f"Temperature: {temp}°C")
        print(f"Condition: {weather_desc}")
        print(f"Humidity: {humidity}%")
        print(f"Wind Speed: {wind} km/h")
        print("=" * 40)
        
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    get_weather()