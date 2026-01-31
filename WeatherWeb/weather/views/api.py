from django.views import View
from django.http import JsonResponse, HttpResponseBadRequest
from weather.services.weather_service import get_current_weather
from weather.services.gis_utils import validate_coordinates

class WeatherAPIView(View):
    def get(self, request):
        try:
            lat = float(request.GET.get('lat'))
            lng = float(request.GET.get('lng'))
            validate_coordinates(lat, lng)
            weather = get_current_weather(lat, lng)
            return JsonResponse(weather)
        except Exception as e:
            return HttpResponseBadRequest(str(e))
