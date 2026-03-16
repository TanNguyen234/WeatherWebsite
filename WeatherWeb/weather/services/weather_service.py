"""
Weather Service - Fetch current weather data from OpenWeatherMap API.
Weather data is fetched on demand, never stored.
"""
import os
import math
from datetime import datetime, timedelta
import requests

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


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


def get_hourly_weather_forecast(lat: float, lng: float, hours: int = 12) -> list[dict]:
    """Return hourly weather forecast for the next N hours.

    Uses Open-Meteo (no key required) and falls back to deterministic projection.
    """
    if hours < 1 or hours > 48:
        raise ValueError("hours phải nằm trong khoảng [1, 48]")

    try:
        return _fetch_hourly_from_open_meteo(lat, lng, hours)
    except Exception:
        current = get_current_weather(lat, lng)
        return _project_hourly_from_current(current, hours)


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


def _description_from_open_meteo_code(code: int) -> str:
    mapping = {
        0: "Trời quang",
        1: "Ít mây",
        2: "Mây rải rác",
        3: "Nhiều mây",
        45: "Sương mù",
        48: "Sương mù đóng băng",
        51: "Mưa phùn nhẹ",
        53: "Mưa phùn vừa",
        55: "Mưa phùn nặng hạt",
        61: "Mưa nhẹ",
        63: "Mưa vừa",
        65: "Mưa to",
        71: "Tuyết nhẹ",
        73: "Tuyết vừa",
        75: "Tuyết dày",
        80: "Mưa rào nhẹ",
        81: "Mưa rào vừa",
        82: "Mưa rào mạnh",
        95: "Giông",
    }
    return mapping.get(code, "Biến đổi")


def _fetch_hourly_from_open_meteo(lat: float, lng: float, hours: int) -> list[dict]:
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "timezone": "auto",
        "forecast_days": 3,
    }
    resp = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    hourly = payload.get("hourly", {})
    timestamps = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    humidities = hourly.get("relative_humidity_2m", [])
    winds = hourly.get("wind_speed_10m", [])
    codes = hourly.get("weather_code", [])

    if not timestamps or not temperatures or not humidities or not winds:
        raise ValueError("Open-Meteo thiếu dữ liệu dự báo theo giờ")

    now_local = datetime.now()
    output = []
    for idx, ts in enumerate(timestamps):
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue

        if dt < now_local:
            continue

        output.append(
            {
                "hour_offset": len(output) + 1,
                "timestamp": ts,
                "temperature": round(float(temperatures[idx]), 1),
                "humidity": int(round(float(humidities[idx]), 0)),
                "wind_speed": round(float(winds[idx]), 1),
                "description": _description_from_open_meteo_code(int(codes[idx])) if idx < len(codes) else "Biến đổi",
                "source": "open-meteo-hourly",
            }
        )

        if len(output) >= hours:
            break

    if len(output) < hours:
        raise ValueError("Không đủ dữ liệu dự báo theo giờ từ Open-Meteo")

    return output


def _project_hourly_from_current(current: dict, hours: int) -> list[dict]:
    """Deterministic fallback projection when hourly API is unavailable."""
    temp0 = float(current.get("temperature", 27.0))
    humidity0 = float(current.get("humidity", 70.0))
    wind0 = float(current.get("wind_speed", 3.5))

    series = []
    now = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    for h in range(1, hours + 1):
        cycle = math.sin((h / 24.0) * math.pi * 2)
        temperature = round(temp0 + cycle * 1.2 - (h * 0.03), 1)
        humidity = int(round(max(20, min(100, humidity0 - cycle * 3.5 + h * 0.1)), 0))
        wind_speed = round(max(0.0, wind0 + abs(cycle) * 0.8 - h * 0.02), 1)

        series.append(
            {
                "hour_offset": h,
                "timestamp": (now.replace(minute=0, second=0, microsecond=0)).isoformat(),
                "temperature": temperature,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "description": current.get("description", "Biến đổi"),
                "source": "hourly-projection",
            }
        )
        now += timedelta(hours=1)

    return series


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

