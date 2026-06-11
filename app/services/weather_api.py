import requests

def get_weather_forecast(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation,temperature_2m",
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "forecast_days": 7,
        "timezone": "auto"
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def search_location(name):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": name,
        "count": 5,
        "language": "en",
        "format": "json"
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()