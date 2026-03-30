import requests
import json

def get_weather_san_francisco():
    """
    Fetches weather data for San Francisco from wttr.in and prints a summary.
    """
    city = "San Francisco"
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
        feels_like_f = current_condition['FeelsLikeF']
        humidity = current_condition['humidity']
        wind_speed_mph = current_condition['windspeedMiles']
        wind_speed_kmph = current_condition['windspeedKmph']

        print(f"Weather in {city}:")
        print(f"  Description: {weather_desc}")
        print(f"  Temperature: {temp_c}°C ({temp_f}°F)")
        print(f"  Feels like: {feels_like_c}°C ({feels_like_f}°F)")
        print(f"  Humidity: {humidity}%")
        print(f"  Wind: {wind_speed_kmph} km/h ({wind_speed_mph} mph)")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected request error occurred: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"JSON decoding error: {json_err}. Response content: {response.text if 'response' in locals() else 'N/A'}")
    except KeyError as key_err:
        print(f"Error parsing weather data: Missing key {key_err}. Data structure might have changed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    get_weather_san_francisco()