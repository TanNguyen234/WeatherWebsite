"""
Weather Service - Fetch current weather data from OpenWeatherMap API.
Weather data is fetched on demand, never stored.
"""
import os
import math
import requests

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_current_weather(lat: float, lng: float) -> dict:
    """
    Return current weather for the given coordinates.

    Tries the real OpenWeatherMap API first; falls back to a deterministic
    approximation when no API key is configured or the request fails.

    Returns:
        {temperature, description, humidity, wind_speed, feels_like,
         pressure, visibility, icon, weather_main}
    """
    if OPENWEATHER_API_KEY:
        try:
            return _fetch_current_from_api(lat, lng)
        except Exception:
            pass

    return _approximate_current_weather(lat, lng)


# ---------------------------------------------------------------------------
# Real API
# ---------------------------------------------------------------------------

def _fetch_current_from_api(lat: float, lng: float) -> dict:
    """Fetch current weather from OpenWeatherMap /data/2.5/weather."""
    params = {
        "lat": lat,
        "lon": lng,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "vi",
    }
    resp = requests.get(OPENWEATHER_CURRENT_URL, params=params, timeout=8)
    resp.raise_for_status()
    d = resp.json()

    return {
        "temperature":   round(d["main"]["temp"], 1),
        "feels_like":    round(d["main"].get("feels_like", d["main"]["temp"]), 1),
        "temp_min":      round(d["main"].get("temp_min", d["main"]["temp"]), 1),
        "temp_max":      round(d["main"].get("temp_max", d["main"]["temp"]), 1),
        "humidity":      d["main"]["humidity"],
        "pressure":      d["main"].get("pressure", 1013),
        "wind_speed":    round(d["wind"]["speed"], 1),
        "wind_deg":      d["wind"].get("deg", 0),
        "visibility":    d.get("visibility", 10000),
        "description":   d["weather"][0]["description"].capitalize(),
        "weather_main":  d["weather"][0]["main"],
        "icon":          d["weather"][0]["icon"],
        "clouds":        d.get("clouds", {}).get("all", 0),
        "rain_1h":       d.get("rain", {}).get("1h", 0),
        "source":        "openweathermap",
    }


# ---------------------------------------------------------------------------
# Deterministic approximation (no API key)
# ---------------------------------------------------------------------------

def _approximate_current_weather(lat: float, lng: float) -> dict:
    """
    Physics-inspired approximation so the app is usable without an API key.
    Values are deterministic for the same coordinates (no random).
    """
    # Latitude-based temperature model (rough tropics/poles gradient)
    base_temp = 28.0 - abs(lat - 12.0) * 0.45
    # Coastal effect (Vietnam coast ~ 108–110 °E)
    coastal_factor = max(0.0, 1.0 - abs(lng - 109.0) / 5.0)
    base_temp += coastal_factor * 1.5

    # Deterministic season offset using sine (no random)
    # Uses lat + lng as a seed proxy
    season_offset = math.sin(math.radians(lat * 3.7 + lng * 1.3)) * 2.5

    temperature = round(base_temp + season_offset, 1)
    feels_like  = round(temperature - 1.2, 1)

    # Humidity: higher in coastal/low-latitude areas
    humidity = int(min(95, max(40, 72 + coastal_factor * 10 - abs(lat - 15) * 0.4)))

    # Wind: simple lat-based trade wind model
    wind_speed = round(2.5 + abs(math.cos(math.radians(lat))) * 2.0, 1)

    pressure = int(1013 + math.sin(math.radians(lat * 7)) * 8)

    # Pick a description deterministically
    descriptions = [
        ("Clear sky",        "Clear",   "01d"),
        ("Partly cloudy",    "Clouds",  "02d"),
        ("Scattered clouds", "Clouds",  "03d"),
        ("Light rain",       "Rain",    "10d"),
        ("Overcast",         "Clouds",  "04d"),
    ]
    idx = int(abs(lat * 13.7 + lng * 7.3)) % len(descriptions)
    desc, main, icon = descriptions[idx]

    return {
        "temperature":   temperature,
        "feels_like":    feels_like,
        "temp_min":      round(temperature - 2.0, 1),
        "temp_max":      round(temperature + 2.0, 1),
        "humidity":      humidity,
        "pressure":      pressure,
        "wind_speed":    wind_speed,
        "wind_deg":      int(abs(lat * 17 + lng * 11)) % 360,
        "visibility":    10000,
        "description":   desc,
        "weather_main":  main,
        "icon":          icon,
        "clouds":        int(humidity * 0.6),
        "rain_1h":       0,
        "source":        "approximation",
    }

