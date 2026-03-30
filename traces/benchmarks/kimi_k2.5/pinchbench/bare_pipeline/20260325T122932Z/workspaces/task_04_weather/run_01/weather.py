import json
import urllib.request
import urllib.error

def get_weather():
    """Fetch and display weather for San Francisco using wttr.in API."""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        # Make HTTP request
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Extract current weather
        current = data['current_condition'][0]
        location = data['nearest_area'][0]
        
        # Parse data
        temp_c = current['temp_C']
        temp_f = current['temp_F']
        feels_like_c = current['FeelsLikeC']
        humidity = current['humidity']
        weather_desc = current['weatherDesc'][0]['value']
        wind_speed = current['windspeedKmph']
        city = location['areaName'][0]['value']
        region = location['region'][0]['value']
        
        # Print summary
        print(f"Weather in {city}, {region}")
        print(f"Current: {weather_desc}")
        print(f"Temperature: {temp_c}°C / {temp_f}°F")
        print(f"Feels like: {feels_like_c}°C")
        print(f"Humidity: {humidity}%")
        print(f"Wind: {wind_speed} km/h")
        
    except urllib.error.URLError as e:
        print(f"Network error: Unable to fetch weather data")
        print(f"Reason: {e.reason}")
    except urllib.error.HTTPError as e:
        print(f"HTTP error: {e.code} - {e.reason}")
    except json.JSONDecodeError:
        print("Error: Unable to parse weather data")
    except KeyError as e:
        print(f"Error: Unexpected data format (missing key: {e})")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    get_weather()