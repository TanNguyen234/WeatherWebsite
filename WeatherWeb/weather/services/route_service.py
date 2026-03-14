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
        weather = get_current_weather(point['latitude'], point['longitude'])
        
        route_data.append({
            'latitude': point['latitude'],
            'longitude': point['longitude'],
            'index': point['index'],
            'weather': weather
        })
    
    return route_data
