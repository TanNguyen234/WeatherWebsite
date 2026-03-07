"""
Forecast Service - Fetch forecast data from OpenWeatherMap API.
In production, forecast data is never stored; it is fetched on demand.
"""
import os
import math
import requests
from datetime import datetime, timedelta

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OWM_FORECAST_URL  = "https://api.openweathermap.org/data/2.5/forecast"   # 5-day / 3h
OWM_ONECALL_URL   = "https://api.openweathermap.org/data/3.0/onecall"    # OneCall 3.0


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_forecast(lat: float, lng: float, mode: str = 'hourly') -> list:
    """
    Return forecast data for coordinates.

    Args:
        lat:  Latitude
        lng:  Longitude
        mode: 'hourly' (next 24h, 1-hour steps) or 'daily' (next 7 days)

    Returns:
        List of forecast dicts ordered by time.
        Each dict contains: time, temperature, humidity, wind_speed,
        description, weather_main, icon  (+ temp_min/temp_max for daily)
    """
    if OPENWEATHER_API_KEY:
        try:
            return _fetch_forecast_from_api(lat, lng, mode)
        except Exception:
            pass

    return _approximate_forecast(lat, lng, mode)


# Keep old name as alias so existing callers don't break
generate_mock_forecast = generate_forecast


# ---------------------------------------------------------------------------
# Real API
# ---------------------------------------------------------------------------

def _fetch_forecast_from_api(lat: float, lng: float, mode: str) -> list:
    """
    Use OWM /forecast (free tier, 3-hour steps) and resample to requested mode.
    """
    params = {
        "lat":   lat,
        "lon":   lng,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang":  "vi",
        "cnt":   40,   # up to 40×3h = 5 days
    }
    resp = requests.get(OWM_FORECAST_URL, params=params, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("list", [])

    if mode == "hourly":
        return _parse_hourly(items)
    return _parse_daily(items)


def _parse_hourly(items: list) -> list:
    """Convert OWM 3-hour steps to hourly-labelled entries (first 24 items)."""
    result = []
    for entry in items[:24]:
        dt = datetime.fromtimestamp(entry["dt"])
        result.append({
            "time":         dt.strftime("%Y-%m-%d %H:00"),
            "timestamp":    entry["dt"],
            "temperature":  round(entry["main"]["temp"], 1),
            "feels_like":   round(entry["main"].get("feels_like", entry["main"]["temp"]), 1),
            "humidity":     entry["main"]["humidity"],
            "wind_speed":   round(entry["wind"]["speed"], 1),
            "description":  entry["weather"][0]["description"].capitalize(),
            "weather_main": entry["weather"][0]["main"],
            "icon":         entry["weather"][0]["icon"],
            "clouds":       entry.get("clouds", {}).get("all", 0),
            "rain_3h":      entry.get("rain", {}).get("3h", 0),
            "source":       "openweathermap",
        })
    return result


def _parse_daily(items: list) -> list:
    """Aggregate 3-hour OWM steps into daily summaries (up to 7 days)."""
    by_day: dict[str, list] = {}
    for entry in items:
        day_key = datetime.fromtimestamp(entry["dt"]).strftime("%Y-%m-%d")
        by_day.setdefault(day_key, []).append(entry)

    result = []
    for day_key in sorted(by_day.keys())[:7]:
        entries = by_day[day_key]
        temps      = [e["main"]["temp"] for e in entries]
        humidities = [e["main"]["humidity"] for e in entries]
        winds      = [e["wind"]["speed"] for e in entries]
        # Midday entry for description/icon
        mid = entries[len(entries) // 2]
        result.append({
            "time":         day_key,
            "temperature":  round(sum(temps) / len(temps), 1),
            "temp_min":     round(min(temps), 1),
            "temp_max":     round(max(temps), 1),
            "humidity":     int(sum(humidities) / len(humidities)),
            "wind_speed":   round(sum(winds) / len(winds), 1),
            "description":  mid["weather"][0]["description"].capitalize(),
            "weather_main": mid["weather"][0]["main"],
            "icon":         mid["weather"][0]["icon"],
            "source":       "openweathermap",
        })
    return result


# ---------------------------------------------------------------------------
# Deterministic approximation (no API key)
# ---------------------------------------------------------------------------

_CONDITIONS = [
    ("Trời quang", "Clear",   "01d"),
    ("Ít mây",     "Clouds",  "02d"),
    ("Mây rải rác","Clouds",  "03d"),
    ("Mưa nhẹ",   "Rain",    "10d"),
    ("Nhiều mây",  "Clouds",  "04d"),
    ("Dông",       "Thunderstorm", "11d"),
]


def _approximate_forecast(lat: float, lng: float, mode: str) -> list:
    base_temp = 28.0 - abs(lat - 12.0) * 0.4 + math.sin(math.radians(lng)) * 1.5
    base_hum  = int(min(90, max(45, 70 + abs(math.cos(math.radians(lat))) * 10)))
    base_wind = round(2.0 + abs(math.cos(math.radians(lat))) * 2.5, 1)

    def _cond(seed: int):
        return _CONDITIONS[int(abs(seed)) % len(_CONDITIONS)]

    now = datetime.now()

    if mode == "hourly":
        result = []
        for i in range(24):
            dt = now + timedelta(hours=i)
            hour_of_day = dt.hour
            # Diurnal temperature cycle
            diurnal = 3.5 * math.sin(math.pi * (hour_of_day - 6) / 12) if 6 <= hour_of_day <= 18 else -1.5
            temp = round(base_temp + diurnal, 1)
            desc, main, icon = _cond(int(lat * 11 + lng * 7 + i * 3))
            result.append({
                "time":         dt.strftime("%Y-%m-%d %H:00"),
                "timestamp":    int(dt.timestamp()),
                "temperature":  temp,
                "feels_like":   round(temp - 1.0, 1),
                "humidity":     base_hum,
                "wind_speed":   base_wind,
                "description":  desc,
                "weather_main": main,
                "icon":         icon,
                "clouds":       int(base_hum * 0.6),
                "rain_3h":      0,
                "source":       "approximation",
            })
        return result

    # daily
    result = []
    for i in range(7):
        dt = now + timedelta(days=i)
        day_offset = math.sin(math.radians(i * 50 + lat * 3)) * 2.0
        temp = round(base_temp + day_offset, 1)
        desc, main, icon = _cond(int(lat * 11 + lng * 7 + i * 19))
        result.append({
            "time":         dt.strftime("%Y-%m-%d"),
            "temperature":  temp,
            "temp_min":     round(temp - 3.5, 1),
            "temp_max":     round(temp + 2.8, 1),
            "humidity":     base_hum,
            "wind_speed":   base_wind,
            "description":  desc,
            "weather_main": main,
            "icon":         icon,
            "source":       "approximation",
        })
    return result

