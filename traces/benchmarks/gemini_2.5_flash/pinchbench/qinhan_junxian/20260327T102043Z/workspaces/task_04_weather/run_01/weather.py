
import requests
import json
import sys

def get_weather(city="San Francisco"):
    """
    Fetches weather data for a given city from wttr.in and prints a summary.
    """
    url = f"https://wttr.in/{city}?format=j1"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        data = response.json()
        
        # Extract current weather information
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']
        feels_like_c = current_condition['FeelsLikeC']
        humidity = current_condition['humidity']
        wind_speed_kmph = current_condition['windspeedKmph']
        
        summary = f"Weather in {city}:\n"
        summary += f"  Description: {weather_desc}\n"
        summary += f"  Temperature: {temp_c}°C (Feels like: {feels_like_c}°C)\n"
        summary += f"  Humidity: {humidity}%\n"
        summary += f"  Wind Speed: {wind_speed_kmph} km/h\n"
        
        print(summary)
        
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to wttr.in. Please check your internet connection.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: Request to wttr.in timed out.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON response from wttr.in. API response might be malformed.", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing key in JSON response: {e}. API response structure might have changed.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    get_weather("San Francisco")
