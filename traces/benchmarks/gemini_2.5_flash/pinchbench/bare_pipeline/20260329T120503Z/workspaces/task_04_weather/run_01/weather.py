import requests
import json

def get_weather(city="San Francisco"):
    """
    Fetches weather data for a given city using the wttr.in API.
    """
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        weather_data = response.json()

        # Extract relevant information
        current_condition = weather_data['current_condition'][0]
        area = weather_data['nearest_area'][0]['areaName'][0]['value']
        country = weather_data['nearest_area'][0]['country'][0]['value']

        temp_c = current_condition['temp_C']
        temp_f = current_condition['temp_F']
        weather_desc = current_condition['weatherDesc'][0]['value']
        humidity = current_condition['humidity']
        wind_speed_kmph = current_condition['windspeedKmph']
        wind_speed_miles = current_condition['windspeedMiles']

        summary = f"Weather in {area}, {country}:\n"
        summary += f"  Condition: {weather_desc}\n"
        summary += f"  Temperature: {temp_c}°C ({temp_f}°F)\n"
        summary += f"  Humidity: {humidity}%\n"
        summary += f"  Wind: {wind_speed_kmph} km/h ({wind_speed_miles} mph)\n"
        return summary

    except requests.exceptions.HTTPError as e:
        return f"HTTP error occurred: {e}"
    except requests.exceptions.ConnectionError as e:
        return f"Connection error occurred: {e}"
    except requests.exceptions.Timeout as e:
        return f"The request timed out: {e}"
    except requests.exceptions.RequestException as e:
        return f"An unexpected error occurred: {e}"
    except json.JSONDecodeError:
        return "Failed to decode JSON response."
    except KeyError as e:
        return f"Failed to parse weather data: Missing key {e}. Response might be malformed."

if __name__ == "__main__":
    weather_summary = get_weather("San Francisco")
    print(weather_summary)