import requests
import json

def get_weather():
    """Fetch weather data for San Francisco using wttr.in API"""
    url = "https://wttr.in/San_Francisco?format=j1"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract current weather data
        current = data.get('current_condition', [{}])[0]
        
        # Parse relevant information
        temp = current.get('temp_C', 'N/A')
        feels_like = current.get('FeelsLikeC', 'N/A')
        humidity = current.get('humidity', 'N/A')
        weather_desc = current.get('weather', [{}])[0].get('main', 'N/A')
        wind = current.get('windspeedKmph', 'N/A')
        
        # Print summary
        print("=" * 50)
        print("Weather Summary - San Francisco")
        print("=" * 50)
        print(f"Temperature: {temp}°C")
        print(f"Feels Like: {feels_like}°C")
        print(f"Condition: {weather_desc}")
        print(f"Humidity: {humidity}%")
        print(f"Wind Speed: {wind} km/h")
        print("=" * 50)
        
    except requests.exceptions.Timeout:
        print("Error: Request timed out. Please check your network connection.")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to weather service. Please check your internet connection.")
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error occurred - {e}")
    except json.JSONDecodeError:
        print("Error: Failed to parse weather data.")
    except Exception as e:
        print(f"Error: An unexpected error occurred - {e}")

if __name__ == "__main__":
    get_weather()
