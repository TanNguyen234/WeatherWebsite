import json
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse
from weather.services.gis_utils import list_user_locations, serialize_locations
from weather.services.compare_service import compare_locations


class CompareView(View):
    """
    Compare view - Spatial comparison across multiple points
    """
    template_name = "weather/compare.html"

    def get(self, request):
        """
        Load compare page with user's saved locations
        """
        locations = []
        
        if request.user.is_authenticated:
            locations = list_user_locations(request.user)

        context = {
            'locations': locations,
            'locations_json': json.dumps(serialize_locations(locations))
        }

        return render(request, self.template_name, context)
