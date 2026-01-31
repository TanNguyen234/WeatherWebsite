from django.views import View
from django.shortcuts import render
from django.http import JsonResponse

class ForecastView(View):
    template_name = "forecast.html"

    def get(self, request):
        # Pseudo CK: provide mock locations for dropdown
        locations = [
            {"id": 1, "name": "Hanoi", "latitude": 21.0285, "longitude": 105.8542},
            {"id": 2, "name": "Ho Chi Minh City", "latitude": 10.7769, "longitude": 106.7009},
        ]
        return render(request, self.template_name, {"locations": locations})

    def post(self, request):
        # Always return static mock data for forecast
        # In real app, parse POST and call service
        data = {
            "hour": [
                {"time": "2026-01-31 09:00", "temp": 22.5, "rain": 0, "wind": 2.1, "desc": "Clear sky"},
                {"time": "2026-01-31 12:00", "temp": 25.2, "rain": 0, "wind": 2.8, "desc": "Few clouds"},
                {"time": "2026-01-31 15:00", "temp": 27.0, "rain": 0.2, "wind": 3.0, "desc": "Light rain"},
                {"time": "2026-01-31 18:00", "temp": 24.8, "rain": 0, "wind": 2.5, "desc": "Clear sky"},
                {"time": "2026-01-31 21:00", "temp": 21.3, "rain": 0, "wind": 1.9, "desc": "Clear sky"},
            ],
            "day": [
                {"time": "2026-01-31", "temp": 25.0, "rain": 0.5, "wind": 2.5, "desc": "Partly cloudy"},
                {"time": "2026-02-01", "temp": 26.2, "rain": 0, "wind": 2.7, "desc": "Clear sky"},
                {"time": "2026-02-02", "temp": 24.8, "rain": 1.2, "wind": 3.1, "desc": "Showers"},
                {"time": "2026-02-03", "temp": 23.5, "rain": 0, "wind": 2.0, "desc": "Clear sky"},
                {"time": "2026-02-04", "temp": 22.9, "rain": 0, "wind": 1.8, "desc": "Clear sky"},
            ]
        }
        return JsonResponse(data)
