import urllib.request
import urllib.error

def get_weather():
    """Fetch weather data for San Francisco using wttr.in API"""
    url = "https://wttr.in/San_Francisco?format=3"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            weather_data = response.read().decode('utf-8')
            print(f"Weather in San Francisco:")
            print(weather_data)
    except urllib.error.URLError as e:
        print(f"Error fetching weather data: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    get_weather()