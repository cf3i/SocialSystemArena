import urllib.request
import json

def get_weather():
    """Fetch weather data for San Francisco using wttr.in API"""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Extract current weather
        current = data.get('current_condition', [{}])[0]
        
        if current:
            temp = current.get('temp_C', 'N/A')
            condition = current.get('weatherDesc', [{}])[0].get('value', 'N/A')
            humidity = current.get('humidity', 'N/A')
            wind = current.get('windspeedKmph', 'N/A')
            
            print("=" * 40)
            print("Weather Summary - San Francisco")
            print("=" * 40)
            print(f"Temperature: {temp}°C")
            print(f"Condition: {condition}")
            print(f"Humidity: {humidity}%")
            print(f"Wind Speed: {wind} km/h")
            print("=" * 40)
        else:
            print("No weather data available")
            
    except urllib.error.URLError as e:
        print(f"Network error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_weather()