import json
from django.views import View
from django.shortcuts import render
from weather.services.gis_utils import list_user_locations, serialize_locations
from weather.models import Route


class RouteView(View):
    """
    Route view - Linear spatial analysis
    """
    template_name = "weather/route.html"

    def get(self, request):
        """
        Load route page with user's locations and saved routes
        """
        locations = []
        routes = []
        is_authenticated = request.user.is_authenticated
        
        if is_authenticated:
            locations = list_user_locations(request.user)
            routes = Route.objects.filter(user=request.user).select_related(
                'start_location', 'end_location'
            )

        # Serialize routes
        routes_data = [
            {
                'id': r.id,
                'name': r.name,
                'start_location': {
                    'id': r.start_location.id,
                    'name': r.start_location.name,
                    'latitude': r.start_location.latitude,
                    'longitude': r.start_location.longitude
                },
                'end_location': {
                    'id': r.end_location.id,
                    'name': r.end_location.name,
                    'latitude': r.end_location.latitude,
                    'longitude': r.end_location.longitude
                }
            }
            for r in routes
        ]

        context = {
            'locations': locations,
            'locations_json': json.dumps(serialize_locations(locations)),
            'routes': routes,
            'routes_json': json.dumps(routes_data),
            'is_authenticated': is_authenticated
        }

        return render(request, self.template_name, context)
