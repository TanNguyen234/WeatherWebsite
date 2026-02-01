"""
GIS Utilities - Spatial operations and data transformations
All GIS-related logic lives here (pure functions when possible)
"""
from django.core.exceptions import ValidationError
from weather.models import UserLocation, LocationGroup


def validate_coordinates(lat, lng):
    """
    Validate latitude and longitude values
    Returns True if valid, raises ValidationError otherwise
    """
    if lat is None or lng is None:
        raise ValidationError("Coordinates cannot be None")
    
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        raise ValidationError("Coordinates must be numeric")
    
    if not (-90 <= lat <= 90):
        raise ValidationError(f"Latitude must be between -90 and 90, got {lat}")
    
    if not (-180 <= lng <= 180):
        raise ValidationError(f"Longitude must be between -180 and 180, got {lng}")
    
    return True


def create_user_location(user, lat, lng, name=None):
    """
    Create a new user location (spatial intent persistence)
    """
    validate_coordinates(lat, lng)
    
    location = UserLocation.objects.create(
        user=user,
        latitude=lat,
        longitude=lng,
        name=name or f"Point ({lat:.4f}, {lng:.4f})"
    )
    return location


def list_user_locations(user):
    """
    Get all locations for a user
    """
    return list(UserLocation.objects.filter(user=user).order_by('-created_at'))


def get_location_by_id(user, location_id):
    """
    Get a specific location by ID
    """
    return UserLocation.objects.filter(user=user, id=location_id).first()


def delete_user_location(user, location_id):
    """
    Delete a user location
    """
    return UserLocation.objects.filter(user=user, id=location_id).delete()


def list_user_groups(user):
    """
    Get all location groups for a user
    """
    return list(LocationGroup.objects.filter(user=user).order_by('-created_at'))


def serialize_locations(locations):
    """
    Serialize location objects to JSON-safe dictionaries
    """
    if not locations:
        return []
    
    return [
        {
            'id': loc.id,
            'name': loc.name or f"Point ({loc.latitude:.4f}, {loc.longitude:.4f})",
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'created_at': loc.created_at.isoformat() if loc.created_at else None
        }
        for loc in locations
    ]


def serialize_groups(groups):
    """
    Serialize group objects to JSON-safe dictionaries
    """
    if not groups:
        return []
    
    return [
        {
            'id': grp.id,
            'name': grp.name,
            'created_at': grp.created_at.isoformat() if grp.created_at else None
        }
        for grp in groups
    ]


def interpolate_points(lat1, lng1, lat2, lng2, n):
    """
    Generate n evenly spaced points along a line between two coordinates
    Used for route weather analysis
    """
    if n < 2:
        n = 2
    
    points = []
    for i in range(n):
        ratio = i / (n - 1)
        lat = lat1 + (lat2 - lat1) * ratio
        lng = lng1 + (lng2 - lng1) * ratio
        points.append({
            'latitude': round(lat, 6),
            'longitude': round(lng, 6),
            'index': i
        })
    
    return points


def calculate_distance_km(lat1, lng1, lat2, lng2):
    """
    Calculate distance between two points using Haversine formula
    Returns distance in kilometers
    """
    import math
    
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c