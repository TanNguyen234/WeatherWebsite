"""
API Views - JSON endpoints for AJAX requests
"""
import json
import os
import requests as http_requests
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
from weather.services.forecast_service import generate_forecast as generate_mock_forecast
from weather.services.compare_service import compare_locations, get_mock_weather
from weather.services.route_service import generate_route_weather
from weather.services.layer_config import get_available_layers, get_layer_by_id
from weather.models import UserLocation, Route


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
    Proxy GET /api/route-geometry/?slat=&slng=&elat=&elng= → OSRM.

    Country-aware routing strategy
    --------------------------------
    1. Reverse-geocode both endpoints via Nominatim to detect their ISO country code.
    2. If they are in the **same country**, use a 3-waypoint OSRM call
       (start → geographic midpoint → end) which forces the engine to stay close
       to the direct in-country path and prevents cross-border detours.
    3. After retrieving the geometry, validate every coordinate against a known
       country bounding box.  If any point falls outside, the response includes
       ``cross_border: true`` as a non-fatal warning for the UI.

    Returns: { geometry (GeoJSON LineString), distance (m), duration (s),
               country (ISO-2 or null), cross_border (bool) }
    """

    # Known country bounding boxes  (minlat, minlng, maxlat, maxlng)
    # Extend this dict when new countries are needed.
    COUNTRY_BBOX = {
        'VN': ( 8.18, 102.14, 23.40, 109.47),
        'TH': ( 5.63,  97.34, 20.46, 105.64),
        'KH': (10.49, 102.33, 14.68, 107.63),
        'LA': (13.91, 100.12, 22.50, 107.64),
        'MM': ( 9.78,  92.18, 28.55, 101.17),
        'CN': (18.16,  73.56, 53.56, 134.77),
        'MY': ( 0.85,  99.64,  7.36, 119.27),
        'ID': (-11.01, 94.97,  6.08, 141.02),
        'PH': ( 4.64, 116.93, 21.12, 126.60),
        'JP': (24.04, 122.93, 45.52, 153.99),
        'KR': (33.11, 124.61, 38.61, 130.92),
        'IN': ( 6.75,  68.11, 35.67,  97.40),
        'US': (18.91, -171.79, 71.36, -66.94),
        'DE': (47.27,   5.87, 55.06,  15.04),
        'FR': (41.33,  -5.14, 51.09,   9.56),
        'GB': (49.96,  -8.62, 60.84,   1.77),
    }

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_country_code(self, lat, lng):
        """
        Reverse-geocode a point using Nominatim and return its ISO-2 country
        code (uppercase), or None on failure.
        Uses ``zoom=3`` to request only the country-level placename, keeping
        the response small and the call fast.
        """
        try:
            resp = http_requests.get(
                'https://nominatim.openstreetmap.org/reverse',
                params={
                    'lat': lat, 'lon': lng,
                    'format': 'json',
                    'zoom': 3,
                    'addressdetails': 1,
                },
                headers={
                    'User-Agent': 'WeatherGIS/1.0 (educational project)',
                    'Accept-Language': 'en',
                },
                timeout=6,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get('address', {}).get('country_code', '').upper() or None
        except Exception:
            return None

    def _geometry_exits_country(self, coordinates, country_code):
        """
        Return True if any [lon, lat] pair in *coordinates* falls outside
        the bounding box registered for *country_code*.
        Returns False when the country is not in COUNTRY_BBOX (cannot verify).
        """
        bbox = self.COUNTRY_BBOX.get(country_code)
        if not bbox:
            return False
        minlat, minlng, maxlat, maxlng = bbox
        for lon, lat in coordinates:
            if not (minlat <= lat <= maxlat and minlng <= lon <= maxlng):
                return True
        return False

    def _build_waypoint_coords(self, slat, slng, elat, elng, n_intermediate=4):
        """
        Build an OSRM-style coordinate string with *n_intermediate* equally
        spaced waypoints along the straight line from (slat, slng) to
        (elat, elng).  More waypoints = tighter constraint on the path,
        which prevents OSRM from routing through neighbouring countries.

        Returns a semicolon-separated string:  'lng,lat;lng,lat;…'
        """
        points = [(slng, slat)]
        for i in range(1, n_intermediate + 1):
            frac = i / (n_intermediate + 1)
            points.append((
                slng + frac * (elng - slng),
                slat + frac * (elat - slat),
            ))
        points.append((elng, elat))
        return ';'.join(f'{lng:.6f},{lat:.6f}' for lng, lat in points)

    def _call_osrm(self, coords_str):
        """
        Call the public OSRM routing API with the given coordinate string.

        Returns (route_dict, None) on success or (None, JsonResponse) on error.
        *route_dict* has keys: geometry (GeoJSON LineString), distance, duration.
        """
        osrm_url = (
            f'https://router.project-osrm.org/route/v1/driving/'
            f'{coords_str}'
            f'?overview=full&geometries=geojson&steps=false'
        )
        try:
            resp = http_requests.get(
                osrm_url,
                headers={'User-Agent': 'WeatherGIS/1.0'},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            return None, JsonResponse({'error': str(exc)}, status=502)

        if data.get('code') != 'Ok' or not data.get('routes'):
            return None, JsonResponse(
                {'error': 'Không tìm thấy đường giữa hai điểm đã chọn'},
                status=404,
            )
        return data['routes'][0], None

    # ── Main handler ───────────────────────────────────────────────────────

    def get(self, request):
        try:
            slat = float(request.GET['slat'])
            slng = float(request.GET['slng'])
            elat = float(request.GET['elat'])
            elng = float(request.GET['elng'])
        except (KeyError, ValueError):
            return JsonResponse({'error': 'Thiếu hoặc sai tham số tọa độ'}, status=400)

        # ── Step 1: Detect countries of both endpoints in parallel ──────────
        # Two sequential Nominatim calls; timeout is kept short (6 s each).
        start_country = self._get_country_code(slat, slng)
        end_country   = self._get_country_code(elat, elng)
        same_country  = bool(
            start_country and end_country and start_country == end_country
        )

        # ── Step 2: Build OSRM coordinate string ────────────────────────────
        if same_country:
            # Multi-waypoint routing: divide the straight line into N+1 equal
            # segments.  Forcing OSRM to pass through each intermediate point
            # keeps the engine from detouring through neighbouring countries.
            # We try increasingly dense waypoint sets (4 → 8) and raise an
            # error only when the geometry still exits the country after the
            # second attempt.
            coords_str = self._build_waypoint_coords(slat, slng, elat, elng, n_intermediate=4)
        else:
            # Cross-country or undetected: use simple 2-point routing.
            coords_str = f'{slng:.6f},{slat:.6f};{elng:.6f},{elat:.6f}'

        # ── Step 3: Call OSRM (first attempt) ──────────────────────────────
        route, error_response = self._call_osrm(coords_str)
        if error_response:
            return error_response

        geometry_coords = route['geometry']['coordinates']  # [[lon, lat], …]

        # ── Step 4: Validate geometry stays within country; retry if needed ─
        cross_border = False
        if same_country:
            if self._geometry_exits_country(geometry_coords, start_country):
                # First attempt crossed the border – retry with 8 waypoints.
                coords_str_dense = self._build_waypoint_coords(
                    slat, slng, elat, elng, n_intermediate=8
                )
                route2, error_response2 = self._call_osrm(coords_str_dense)
                if error_response2:
                    return error_response2

                geometry_coords2 = route2['geometry']['coordinates']
                if self._geometry_exits_country(geometry_coords2, start_country):
                    # Still crosses border even with dense waypoints – refuse.
                    return JsonResponse(
                        {
                            'error': (
                                'Không tìm được đường đi hoàn toàn trong lãnh thổ '
                                'giữa hai điểm này. Thử chọn điểm gần hơn hoặc '
                                'nằm trên trục đường chính trong nước.'
                            )
                        },
                        status=422,
                    )
                # Dense retry succeeded and stays within country.
                route = route2
                geometry_coords = geometry_coords2

        return JsonResponse({
            'geometry':     route['geometry'],   # GeoJSON LineString
            'distance':     route['distance'],   # metres
            'duration':     route['duration'],   # seconds
            'country':      start_country if same_country else None,
            'cross_border': cross_border,        # always False now (error on True)
        })


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
