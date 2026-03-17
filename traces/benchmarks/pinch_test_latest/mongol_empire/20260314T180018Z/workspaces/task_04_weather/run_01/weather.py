import urllib.request
import json

def get_weather():
    """Fetch weather data for San Francisco using wttr.in API"""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        current = data['current_condition'][0]
        print("=" * 40)
        print("Weather Summary - San Francisco")
        print("=" * 40)
        print(f"Location: San Francisco, CA")
        print(f"Temperature: {current['temp_C']}°C ({current['temp_F']}°F)")
        print(f"Condition: {current['weatherDesc'][0]['value']}")
        print(f"Humidity: {current['humidity']}%")
        print(f"Wind Speed: {current['windspeedKmph']} km/h")
        print(f"Feels Like: {current['FeelsLikeC']}°C")
        print("=" * 40)
        
    except urllib.error.URLError as e:
        print(f"Error: Unable to fetch weather data - {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_weather()