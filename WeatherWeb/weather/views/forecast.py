import json
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse
from weather.services.gis_utils import list_user_locations, serialize_locations
from weather.services.forecast_service import generate_mock_forecast


class ForecastView(View):
    """
    Forecast view - Temporal analysis at fixed point
    """
    template_name = "weather/forecast.html"

    def get(self, request):
        """
        Load forecast page with user's saved locations
        """
        locations = []
        
        if request.user.is_authenticated:
            locations = list_user_locations(request.user)

        context = {
            'locations': locations,
            'locations_json': json.dumps(serialize_locations(locations))
        }

        return render(request, self.template_name, context)

    def post(self, request):
        """
        Generate forecast data for a location
        """
        try:
            data = json.loads(request.body.decode())
            mode = data.get('mode', 'hourly')
            
            # Get coordinates
            lat = data.get('latitude')
            lng = data.get('longitude')
            location_id = data.get('location_id')
            
            if location_id and request.user.is_authenticated:
                from weather.models import UserLocation
                location = UserLocation.objects.get(id=location_id, user=request.user)
                lat = location.latitude
                lng = location.longitude
            
            if lat is None or lng is None:
                return JsonResponse({'error': 'Coordinates required'}, status=400)
            
            forecast = generate_mock_forecast(float(lat), float(lng), mode)
            
            return JsonResponse({
                'forecast': forecast,
                'location': {'latitude': lat, 'longitude': lng}
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
