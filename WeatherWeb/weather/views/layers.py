import json
import os
from django.views import View
from django.shortcuts import render
from weather.services.layer_config import get_available_layers


class LayersView(View):
    """
    Layers page – GIS layer abstraction with real OWM tile overlays.
    """
    template_name = "weather/layers.html"

    def get(self, request):
        layers = get_available_layers()

        # Pass API key to template so JS can build OWM tile URLs.
        # Only expose if it is actually set – the client gracefully handles absence.
        owm_api_key = os.getenv("OPENWEATHER_API_KEY", "")

        context = {
            'layers':      layers,
            'layers_json': json.dumps(layers),
            'owm_api_key': owm_api_key,
        }

        return render(request, self.template_name, context)
