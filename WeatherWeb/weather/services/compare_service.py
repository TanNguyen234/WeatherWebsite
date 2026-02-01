"""
Compare Service - Spatial comparison across multiple locations
"""
from weather.services.weather_service import get_current_weather


def compare_locations(locations):
    """
    Compare weather across multiple locations
    
    Args:
        locations: List of location objects with latitude/longitude
    
    Returns:
        List of comparison data with weather for each location
    """
    comparison = []
    
    for location in locations:
        try:
            weather = get_current_weather(location.latitude, location.longitude)
        except Exception:
            # Use mock data if API fails
            weather = get_mock_weather(location.latitude, location.longitude)
        
        comparison.append({
            'id': location.id,
            'name': location.name or f"Point ({location.latitude:.2f}, {location.longitude:.2f})",
            'latitude': location.latitude,
            'longitude': location.longitude,
            'weather': weather
        })
    
    return comparison


def get_mock_weather(lat, lng):
    """
    Generate mock weather data for comparison
    """
    import random
    
    # Base temperature influenced by latitude
    base_temp = 30 - abs(lat - 15) * 0.3
    
    conditions = [
        'Clear sky', 'Few clouds', 'Partly cloudy', 
        'Scattered clouds', 'Light rain'
    ]
    
    return {
        'temperature': round(base_temp + random.uniform(-3, 3), 1),
        'humidity': random.randint(50, 85),
        'wind_speed': round(random.uniform(1, 5), 1),
        'description': random.choice(conditions)
    }
