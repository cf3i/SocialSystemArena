
import requests
import json
import sys

def get_weather_summary(city="San Francisco"):
    """
    Fetches weather data for a given city from wttr.in and prints a summary.
    """
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Extract relevant information
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']
        temp_f = current_condition['temp_F']
        feels_like_c = current_condition['FeelsLikeC']
        humidity = current_condition['humidity']
        wind_speed_kmph = current_condition['windspeedKmph']

        print(f"Weather in {city}:")
        print(f"  Condition: {weather_desc}")
        print(f"  Temperature: {temp_c}°C ({temp_f}°F)")
        print(f"  Feels like: {feels_like_c}°C")
        print(f"  Humidity: {humidity}%")
        print(f"  Wind Speed: {wind_speed_kmph} km/h")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}", file=sys.stderr)
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}", file=sys.stderr)
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}", file=sys.stderr)
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected request error occurred: {req_err}", file=sys.stderr)
    except json.JSONDecodeError as json_err:
        print(f"Error decoding JSON response: {json_err}", file=sys.stderr)
    except KeyError as key_err:
        print(f"Error parsing weather data (missing key): {key_err}. API response structure might have changed.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    get_weather_summary()
