"""
Layer Configuration - GIS layer abstraction
Defines available weather visualization layers
"""


def get_available_layers():
    """
    Get configuration for all available weather layers
    
    Returns:
        Dict of layer configurations
    """
    return {
        'temperature': {
            'id': 'temperature',
            'name': 'Temperature',
            'icon': '🌡️',
            'unit': '°C',
            'range': {'min': -10, 'max': 40},
            'colors': ['#3b82f6', '#fbbf24', '#ef4444'],
            'default_opacity': 0.7,
            'enabled_by_default': True
        },
        'rain': {
            'id': 'rain',
            'name': 'Precipitation',
            'icon': '🌧️',
            'unit': 'mm',
            'range': {'min': 0, 'max': 50},
            'colors': ['#f0f9ff', '#0ea5e9', '#1e3a8a'],
            'default_opacity': 0.7,
            'enabled_by_default': False
        },
        'wind': {
            'id': 'wind',
            'name': 'Wind Speed',
            'icon': '💨',
            'unit': 'm/s',
            'range': {'min': 0, 'max': 20},
            'colors': ['#d1fae5', '#10b981', '#064e3b'],
            'default_opacity': 0.7,
            'enabled_by_default': False
        },
        'clouds': {
            'id': 'clouds',
            'name': 'Cloud Cover',
            'icon': '☁️',
            'unit': '%',
            'range': {'min': 0, 'max': 100},
            'colors': ['#fefce8', '#9ca3af', '#374151'],
            'default_opacity': 0.7,
            'enabled_by_default': False
        }
    }


def get_layer_by_id(layer_id):
    """
    Get a specific layer configuration
    """
    layers = get_available_layers()
    return layers.get(layer_id)
