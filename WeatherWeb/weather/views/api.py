"""
API Views - JSON endpoints for AJAX requests
"""
import json
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from weather.services.gis_utils import (
    validate_coordinates,
    create_user_location,
    delete_user_location,
    get_location_by_id,
    list_user_locations,
    serialize_locations
)
from weather.services.weather_service import get_current_weather
from weather.services.forecast_service import generate_mock_forecast
from weather.services.compare_service import compare_locations, get_mock_weather
from weather.services.route_service import generate_route_weather
from weather.models import UserLocation, Route


class WeatherAPIView(View):
    """
    Get current weather for coordinates
    """
    def get(self, request):
        try:
            lat = float(request.GET.get('lat'))
            lng = float(request.GET.get('lng'))
            validate_coordinates(lat, lng)
            weather = get_current_weather(lat, lng)
            return JsonResponse(weather)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class LocationAPIView(View):
    """
    CRUD operations for user locations
    """
    def get(self, request):
        """List all user locations"""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Yêu cầu xác thực'}, status=401)
        
        locations = list_user_locations(request.user)
        return JsonResponse({'locations': serialize_locations(locations)})

    def post(self, request):
        """Create a new location"""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Yêu cầu xác thực'}, status=401)
        
        try:
            data = json.loads(request.body.decode())
            lat = float(data.get('latitude'))
            lng = float(data.get('longitude'))
            name = data.get('name')
            
            location = create_user_location(request.user, lat, lng, name)
            weather = get_current_weather(lat, lng)
            
            return JsonResponse({
                'location': {
                    'id': location.id,
                    'name': location.name,
                    'latitude': location.latitude,
                    'longitude': location.longitude
                },
                'weather': weather
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class LocationDetailAPIView(View):
    """
    Single location operations
    """
    def delete(self, request, location_id):
        """Delete a location"""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Yêu cầu xác thực'}, status=401)
        
        try:
            deleted, _ = delete_user_location(request.user, location_id)
            if deleted:
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Không tìm thấy vị trí'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class ForecastAPIView(View):
    """
    Get forecast data
    """
    def post(self, request):
        try:
            data = json.loads(request.body.decode())
            mode = data.get('mode', 'hourly')
            
            lat = data.get('latitude')
            lng = data.get('longitude')
            location_id = data.get('location_id')
            
            if location_id and request.user.is_authenticated:
                location = get_location_by_id(request.user, location_id)
                if location:
                    lat = location.latitude
                    lng = location.longitude
            
            if lat is None or lng is None:
                return JsonResponse({'error': 'Yêu cầu tọa độ'}, status=400)
            
            forecast = generate_mock_forecast(float(lat), float(lng), mode)
            
            return JsonResponse({
                'forecast': forecast,
                'location': {'latitude': lat, 'longitude': lng}
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class CompareAPIView(View):
    """
    Compare weather across multiple locations
    """
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Yêu cầu xác thực'}, status=401)
        
        try:
            data = json.loads(request.body.decode())
            location_ids = data.get('location_ids', [])
            
            if len(location_ids) < 2:
                return JsonResponse({'error': 'Cần ít nhất 2 vị trí'}, status=400)
            
            locations = UserLocation.objects.filter(
                user=request.user,
                id__in=location_ids
            )
            
            comparison = compare_locations(list(locations))
            
            return JsonResponse({'comparison': comparison})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class RouteAPIView(View):
    """
    Get route weather analysis
    """
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Yêu cầu xác thực'}, status=401)
        
        try:
            data = json.loads(request.body.decode())
            start_id = data.get('start_id')
            end_id = data.get('end_id')
            point_count = data.get('point_count', 5)
            
            start_location = get_location_by_id(request.user, start_id)
            end_location = get_location_by_id(request.user, end_id)
            
            if not start_location or not end_location:
                return JsonResponse({'error': 'Vị trí không hợp lệ'}, status=400)
            
            route_points = generate_route_weather(start_location, end_location, point_count)
            
            return JsonResponse({
                'route_points': route_points,
                'start': {
                    'latitude': start_location.latitude,
                    'longitude': start_location.longitude
                },
                'end': {
                    'latitude': end_location.latitude,
                    'longitude': end_location.longitude
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class RouteCreateAPIView(View):
    """
    Save a route
    """
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Yêu cầu xác thực'}, status=401)
        
        try:
            data = json.loads(request.body.decode())
            name = data.get('name')
            start_id = data.get('start_id')
            end_id = data.get('end_id')
            
            start_location = get_location_by_id(request.user, start_id)
            end_location = get_location_by_id(request.user, end_id)
            
            if not start_location or not end_location:
                return JsonResponse({'error': 'Vị trí không hợp lệ'}, status=400)
            
            route = Route.objects.create(
                user=request.user,
                name=name,
                start_location=start_location,
                end_location=end_location
            )
            
            return JsonResponse({
                'success': True,
                'route': {
                    'id': route.id,
                    'name': route.name
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
