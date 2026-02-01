import json
from django.views import View
from django.shortcuts import render
from weather.services.gis_utils import (
    list_user_locations,
    serialize_locations,
    list_user_groups,
    serialize_groups
)


class MapView(View):
    """
    Main map view - Single-point spatial interaction
    """
    template_name = "weather/map.html"

    def get(self, request):
        """
        Load map with user's saved locations and groups
        """
        locations = []
        groups = []
        is_authenticated = request.user.is_authenticated

        if is_authenticated:
            locations = list_user_locations(request.user)
            groups = list_user_groups(request.user)

        context = {
            'locations_json': json.dumps(serialize_locations(locations)),
            'groups_json': json.dumps(serialize_groups(groups)),
            'is_authenticated': is_authenticated
        }

        return render(request, self.template_name, context)