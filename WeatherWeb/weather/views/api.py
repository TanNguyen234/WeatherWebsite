"""
API Views - JSON endpoints for AJAX requests
"""
import json
import os
import requests as http_requests
import logging
from django.views import View
from django.http import HttpResponse, JsonResponse
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
from weather.services.compare_service import compare_locations
from weather.services.route_service import analyze_route_weather
from weather.services.routing_service import get_route_geometry, RoutingServiceError
from weather.services.layer_config import get_available_layers, get_layer_by_id
from weather.services.prediction_service import get_prediction_comparison
from weather.utils.export import generate_prediction_csv
from weather.utils.visualize import generate_prediction_chart_png, png_to_base64
from weather.models import UserLocation, Route


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Third-party proxy endpoints  (bypass client-side CORS / rate-limiting)
# ---------------------------------------------------------------------------

class GeocodeProxyView(View):
    """
    Proxy GET /api/geocode/?q=<text> → Nominatim.
    Running server-side avoids CORS preflight issues and Nominatim's
    browser-UA restrictions on localhost.
    """
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 2:
            return JsonResponse({'error': 'Query too short'}, status=400)
        try:
            resp = http_requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={
                    'q': query,
                    'format': 'json',
                    'limit': 6,
                    'addressdetails': '0',
                    'accept-language': 'vi',
                },
                headers={
                    'User-Agent': 'WeatherGIS/1.0 (educational project)',
                    'Accept-Language': 'vi',
                },
                timeout=8,
            )
            resp.raise_for_status()
            return JsonResponse(resp.json(), safe=False)
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=502)


class RouteGeometryProxyView(View):
    """
    Thin proxy endpoint that delegates routing to routing_service.
    """
    def get(self, request):
        try:
            slat = float(request.GET['slat'])
            slng = float(request.GET['slng'])
            elat = float(request.GET['elat'])
            elng = float(request.GET['elng'])
        except (KeyError, ValueError):
            return JsonResponse({'error': 'Thiếu hoặc sai tham số tọa độ'}, status=400)
        try:
            payload = get_route_geometry(slat, slng, elat, elng)
            return JsonResponse(payload)
        except RoutingServiceError as exc:
            return JsonResponse({'error': str(exc)}, status=exc.status_code)
        except Exception as exc:
            logger.exception('Unexpected error in route geometry endpoint')
            return JsonResponse({'error': str(exc)}, status=500)


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
class PredictAPIView(View):
    """Return API weather and AI prediction results for comparison UI."""

    def post(self, request):
        try:
            lat, lng, forecast_days, horizon_hours = _extract_predict_input(request)
            payload = get_prediction_comparison(
                float(lat),
                float(lng),
                forecast_days=forecast_days,
                horizon_hours=horizon_hours,
            )
            metric = _extract_metric(request)
            chart_png = generate_prediction_chart_png(payload.get('rows', []), metric=metric)
            payload['chart_image_base64'] = png_to_base64(chart_png)
            return JsonResponse(payload)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


def _extract_metric(request) -> str:
    metric = request.GET.get('metric')
    if metric is None:
        try:
            data = json.loads(request.body.decode()) if request.body else {}
            metric = data.get('metric')
        except Exception:
            metric = None
    metric = str(metric or 'temperature')
    if metric not in {'temperature', 'humidity', 'wind_speed'}:
        return 'temperature'
    return metric


def _extract_predict_input(request):
    data = json.loads(request.body.decode()) if request.body else {}
    lat = data.get('latitude')
    lng = data.get('longitude')
    location_id = data.get('location_id')
    forecast_days = data.get('forecast_days')
    horizon_hours = data.get('horizon_hours')

    if location_id and request.user.is_authenticated:
        location = get_location_by_id(request.user, location_id)
        if location:
            lat = location.latitude
            lng = location.longitude

    if lat is None or lng is None:
        raise ValueError('Yêu cầu tọa độ')

    validate_coordinates(float(lat), float(lng))
    forecast_days = int(forecast_days) if forecast_days is not None else None
    horizon_hours = int(horizon_hours) if horizon_hours is not None else None
    return float(lat), float(lng), forecast_days, horizon_hours


@method_decorator(csrf_exempt, name='dispatch')
class PredictExportCSVView(View):
    """Export prediction results to CSV."""

    def post(self, request):
        try:
            lat, lng, forecast_days, horizon_hours = _extract_predict_input(request)
            payload = get_prediction_comparison(
                lat,
                lng,
                forecast_days=forecast_days,
                horizon_hours=horizon_hours,
            )
            csv_bytes = generate_prediction_csv(payload.get('rows', []))
            response = HttpResponse(csv_bytes, content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="predict_result.csv"'
            return response
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class PredictExportImageView(View):
    """Export prediction visualization as PNG image."""

    def post(self, request):
        try:
            lat, lng, forecast_days, horizon_hours = _extract_predict_input(request)
            metric = _extract_metric(request)
            payload = get_prediction_comparison(
                lat,
                lng,
                forecast_days=forecast_days,
                horizon_hours=horizon_hours,
            )
            png_bytes = generate_prediction_chart_png(payload.get('rows', []), metric=metric)
            response = HttpResponse(png_bytes, content_type='image/png')
            response['Content-Disposition'] = 'attachment; filename="predict_chart.png"'
            return response
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)


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
            point_count = int(data.get('point_count', 5))

            if point_count < 2 or point_count > 20:
                return JsonResponse({'error': 'point_count phải nằm trong khoảng [2, 20]'}, status=400)
            
            start_location = get_location_by_id(request.user, start_id)
            end_location = get_location_by_id(request.user, end_id)
            
            if not start_location or not end_location:
                return JsonResponse({'error': 'Vị trí không hợp lệ'}, status=400)

            if start_location.id == end_location.id:
                return JsonResponse({'error': 'Điểm xuất phát và điểm đích phải khác nhau'}, status=400)
            
            analysis = analyze_route_weather(start_location, end_location, point_count)
            
            return JsonResponse({
                'geometry': analysis['geometry'],
                'distance': analysis['distance'],
                'duration': analysis['duration'],
                'country': analysis.get('country'),
                'cross_border': analysis.get('cross_border', False),
                'route_points': analysis['route_points'],
                'segments': analysis['segments'],
                'summary': analysis['summary'],
                'metadata': analysis['metadata'],
                'start': {
                    'id': start_location.id,
                    'name': start_location.name,
                    'latitude': start_location.latitude,
                    'longitude': start_location.longitude
                },
                'end': {
                    'id': end_location.id,
                    'name': end_location.name,
                    'latitude': end_location.latitude,
                    'longitude': end_location.longitude
                }
            })
        except RoutingServiceError as exc:
            return JsonResponse({'error': str(exc)}, status=exc.status_code)
        except Exception as e:
            logger.exception('Route analysis failed')
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


class LayerConfigAPIView(View):
    """
    Serve weather layer configuration and OWM tile metadata to the client.
    The client uses the tile_url + its own API key parameter to load tiles.
    """

    def get(self, request):
        layers = get_available_layers()
        has_api_key = bool(os.getenv("OPENWEATHER_API_KEY", ""))

        return JsonResponse({
            "layers": layers,
            "has_api_key": has_api_key,
        })


class LayerPointDataAPIView(View):
    """
    Return real weather values at key sample points for a given layer.
    Used to render value-labelled markers on the map alongside tile overlays.
    """

    SAMPLE_POINTS = [
        {"lat": 21.0285, "lng": 105.8542, "name": "Hà Nội"},
        {"lat": 10.7769, "lng": 106.7009, "name": "TP.HCM"},
        {"lat": 16.0544, "lng": 108.2022, "name": "Đà Nẵng"},
        {"lat": 12.2388, "lng": 109.1967, "name": "Nha Trang"},
        {"lat": 20.8449, "lng": 106.6881, "name": "Hải Phòng"},
        {"lat": 10.0452, "lng": 105.7469, "name": "Cần Thơ"},
        {"lat": 16.4637, "lng": 107.5909, "name": "Huế"},
        {"lat": 11.9404, "lng": 108.4583, "name": "Đà Lạt"},
        {"lat": 15.1201, "lng": 108.8021, "name": "Quảng Ngãi"},
        {"lat": 22.3350, "lng": 103.8400, "name": "Lào Cai"},
        {"lat": 18.3350, "lng": 105.9054, "name": "Vinh"},
    ]

    LAYER_FIELD_MAP = {
        "temperature": "temperature",
        "rain":        "rain_1h",
        "wind":        "wind_speed",
        "clouds":      "clouds",
        "pressure":    "pressure",
    }

    def get(self, request):
        layer_id = request.GET.get("layer", "temperature")
        layer_cfg = get_layer_by_id(layer_id)
        if not layer_cfg:
            return JsonResponse({"error": "Unknown layer id"}, status=400)

        field = self.LAYER_FIELD_MAP.get(layer_id, "temperature")
        points_data = []

        for pt in self.SAMPLE_POINTS:
            try:
                weather = get_current_weather(pt["lat"], pt["lng"])
                value = weather.get(field, 0)
            except Exception:
                value = 0

            points_data.append({
                "lat":   pt["lat"],
                "lng":   pt["lng"],
                "name":  pt["name"],
                "value": value,
                "unit":  layer_cfg["unit"],
            })

        return JsonResponse({
            "layer":  layer_id,
            "points": points_data,
        })
