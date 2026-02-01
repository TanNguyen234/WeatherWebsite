"""
Route Service - Linear spatial analysis along a path
"""
from weather.services.gis_utils import interpolate_points
from weather.services.weather_service import get_current_weather


def generate_route_weather(start_location, end_location, point_count=5):
    """
    Generate weather data for points along a route
    
    Args:
        start_location: Start location object
        end_location: End location object
        point_count: Number of points to analyze
    
    Returns:
        List of points with weather data
    """
    # Generate interpolated points
    points = interpolate_points(
        start_location.latitude, start_location.longitude,
        end_location.latitude, end_location.longitude,
        point_count
    )
    
    # Get weather for each point
    route_data = []
    for point in points:
        try:
            weather = get_current_weather(point['latitude'], point['longitude'])
        except Exception:
            weather = get_mock_route_weather(point['latitude'], point['longitude'])
        
        route_data.append({
            'latitude': point['latitude'],
            'longitude': point['longitude'],
            'index': point['index'],
            'weather': weather
        })
    
    return route_data


def get_mock_route_weather(lat, lng):
    """
    Generate mock weather for route point
    """
    import random
    
    base_temp = 30 - abs(lat - 15) * 0.3
    
    conditions = ['Clear sky', 'Few clouds', 'Partly cloudy', 'Scattered clouds']
    
    return {
        'temperature': round(base_temp + random.uniform(-2, 2), 1),
        'humidity': random.randint(55, 80),
        'wind_speed': round(random.uniform(1.5, 4), 1),
        'description': random.choice(conditions)
    }
