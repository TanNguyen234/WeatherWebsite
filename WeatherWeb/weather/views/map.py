from django.views import View
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from weather.services.gis_utils import validate_coordinates, create_location, serialize_locations
from weather.services.weather_service import get_current_weather
from weather.models import UserLocation # Đảm bảo models.py đã đưa ra ngoài views/
import json

class MapView(View):
    template_name = "map.html" # Quy tắc 4.1: Sử dụng namespace cho template

    def get(self, request):
        """
        Xử lý hiển thị bản đồ và nạp các địa điểm đã lưu.
        Quy tắc 3: Weather data fetched on demand, not stored.
        """
        locations_data = []
        
        if request.user.is_authenticated:
            # Quy tắc 2.1: View gọi service, không trực tiếp xử lý database nặng
            user_locations = UserLocation.objects.filter(user=request.user)
            locations_data = serialize_locations(user_locations)

        return render(request, self.template_name, {"locations": locations_data})

    def post(self, request):
        """
        Lưu 'spatial intent' của người dùng (tọa độ click).
        Quy tắc 9.2.2: Persist spatial objects created by users.
        """
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
            
        try:
            data = json.loads(request.body.decode())
            lat = float(data.get("latitude"))
            lng = float(data.get("longitude"))
            name = data.get("name", "New Point")

            # Quy tắc 2.3: Logic kiểm tra tọa độ nằm trong Services
            validate_coordinates(lat, lng)
            
            # Quy tắc 9.1: Lưu đối tượng không gian vào PostgreSQL
            location = create_location(lat, lng, name, user=request.user)
            
            # Quy tắc 3.4: Weather data is fetched on demand
            weather = get_current_weather(lat, lng)

            return JsonResponse({
                "location": {
                    "id": location.id,
                    "name": location.name,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                },
                "weather": weather
            })
        except Exception as e:
            # Quy tắc 7: Logically structured error handling
            return JsonResponse({"error": str(e)}, status=400)