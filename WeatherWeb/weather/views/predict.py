import json
from django.views import View
from django.shortcuts import render
from weather.services.gis_utils import list_user_locations, serialize_locations


class PredictView(View):
    """Predict page with API vs AI comparison."""

    template_name = "weather/predict.html"

    def get(self, request):
        locations = []
        if request.user.is_authenticated:
            locations = list_user_locations(request.user)

        context = {
            "locations": locations,
            "locations_json": json.dumps(serialize_locations(locations)),
        }
        return render(request, self.template_name, context)
