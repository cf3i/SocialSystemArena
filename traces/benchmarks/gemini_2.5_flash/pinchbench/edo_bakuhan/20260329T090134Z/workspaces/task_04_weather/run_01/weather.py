
import requests
import json

def get_weather_summary(location="San Francisco"):
    """
    Fetches weather data for a given location from wttr.in and returns a summary.
    """
    url = f"https://wttr.in/{location}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Extract relevant information
        current_condition = data['current_condition'][0]
        weather_description = current_condition['weatherDesc'][0]['value']
        temperature_c = current_condition['temp_C']
        temperature_f = current_condition['temp_F']
        humidity = current_condition['humidity']
        wind_speed_kmph = current_condition['windspeedKmph']

        summary = (
            f"Weather in {location}:\n"
            f"  Description: {weather_description}\n"
            f"  Temperature: {temperature_c}°C / {temperature_f}°F\n"
            f"  Humidity: {humidity}%\n"
            f"  Wind Speed: {wind_speed_kmph} Kmph"
        )
        return summary

    except requests.exceptions.Timeout:
        return f"Error: Request timed out while fetching weather for {location}."
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to wttr.in for {location}. Check your internet connection."
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP request failed for {location} - {e}"
    except json.JSONDecodeError:
        return f"Error: Could not decode JSON response from wttr.in for {location}."
    except KeyError as e:
        return f"Error: Missing expected data in weather response: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

if __name__ == "__main__":
    summary = get_weather_summary("San Francisco")
    print(summary)
