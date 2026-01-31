from weather.models import UserLocation # Sửa tên model cho khớp với file models.py
from django.core.exceptions import ValidationError

def validate_coordinates(lat, lng):

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValidationError("Invalid latitude or longitude coordinates.")
    return True

def create_location(lat, lng, name=None, user=None):

    validate_coordinates(lat, lng)
    # Khớp với tham số truyền từ MapView (phải có user)
    location = UserLocation.objects.create(
        user=user,
        latitude=lat, 
        longitude=lng, 
        name=name
    )
    return location

def serialize_locations(queryset):

    return [
        {
            "id": loc.id,
            "name": loc.name or f"Point ({loc.latitude:.3f}, {loc.longitude:.3f})",
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "created_at": loc.created_at.isoformat() if loc.created_at else None
        }
        for loc in queryset
    ]