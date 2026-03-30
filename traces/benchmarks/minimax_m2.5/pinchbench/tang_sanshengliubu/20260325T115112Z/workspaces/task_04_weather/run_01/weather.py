import json
import urllib.request
import urllib.error

def get_weather_summary():
    """Fetch weather data for San Francisco from wttr.in and print summary."""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
        
        # Extract current weather from JSON response
        current = data.get("current_condition", [{}])[0]
        
        temp_c = current.get("temp_C", "N/A")
        temp_f = current.get("temp_F", "N/A")
        weather_desc = current.get("weatherDesc", [{}])[0].get("value", "N/A")
        humidity = current.get("humidity", "N/A")
        wind_speed = current.get("windspeedKmph", "N/A")
        
        print("=" * 40)
        print("Weather Summary for San Francisco")
        print("=" * 40)
        print(f"Temperature: {temp_c}C / {temp_f}F")
        print(f"Condition: {weather_desc}")
        print(f"Humidity: {humidity}%")
        print(f"Wind Speed: {wind_speed} km/h")
        print("=" * 40)
        
    except urllib.error.URLError as e:
        print(f"Error: Unable to fetch weather data - {e}")
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse weather data - {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_weather_summary()
