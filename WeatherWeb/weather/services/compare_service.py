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
        weather = get_current_weather(location.latitude, location.longitude)
        
        comparison.append({
            'id': location.id,
            'name': location.name or f"Point ({location.latitude:.2f}, {location.longitude:.2f})",
            'latitude': location.latitude,
            'longitude': location.longitude,
            'weather': weather
        })
    
    return comparison
