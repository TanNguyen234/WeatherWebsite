import json
from django.views import View
from django.shortcuts import render
from weather.services.layer_config import get_available_layers


class LayersView(View):
    """
    Layers view - GIS layer abstraction
    """
    template_name = "weather/layers.html"

    def get(self, request):
        """
        Load layers page with available layer configurations
        """
        layers = get_available_layers()

        context = {
            'layers': layers,
            'layers_json': json.dumps(layers)
        }

        return render(request, self.template_name, context)
