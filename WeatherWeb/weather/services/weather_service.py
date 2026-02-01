"""
Weather Service - Fetch weather data from external API
Weather data is fetched on demand, not stored
"""
import os
import random

# Try to get API key, but don't crash if not set
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_current_weather(lat, lng):
    """
    Get current weather for coordinates
    Falls back to mock data if API is not configured or fails
    
    Args:
        lat: Latitude
        lng: Longitude
    
    Returns:
        Dict with weather data
    """
    if OPENWEATHER_API_KEY:
        try:
            return _fetch_from_api(lat, lng)
        except Exception:
            pass
    
    # Fallback to mock data
    return get_mock_current_weather(lat, lng)


def _fetch_from_api(lat, lng):
    """
    Fetch weather from OpenWeatherMap API
    """
    import requests
    
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


def get_mock_current_weather(lat, lng):
    """
    Generate mock weather data based on coordinates
    Provides realistic-ish data for demonstration
    
    Args:
        lat: Latitude (affects base temperature)
        lng: Longitude
    
    Returns:
        Dict with mock weather data
    """
    # Base temperature influenced by latitude
    # Closer to equator = warmer
    base_temp = 30 - abs(lat - 15) * 0.3
    
    # Add some randomness
    temp = base_temp + random.uniform(-3, 3)
    
    conditions = [
        'Clear sky', 
        'Few clouds', 
        'Partly cloudy', 
        'Scattered clouds',
        'Overcast'
    ]
    
    return {
        "temperature": round(temp, 1),
        "description": random.choice(conditions),
        "humidity": random.randint(50, 85),
        "wind_speed": round(random.uniform(1, 5), 1)
    }
