import os
import requests
from django.core.exceptions import ImproperlyConfigured

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise ImproperlyConfigured("OPENWEATHER_API_KEY not set in environment.")

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_current_weather(lat, lng):
    params = {
        "lat": lat,
        "lon": lng,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    resp = requests.get(OPENWEATHER_URL, params=params, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    return {
        "temperature": data["main"]["temp"],
        "description": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"]
    }
