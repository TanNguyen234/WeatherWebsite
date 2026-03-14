"""
Layer Configuration - GIS layer abstraction
Defines available weather visualization layers with OpenWeatherMap tile integration.
"""
# OpenWeatherMap tile base
OWM_TILE_BASE = "https://tile.openweathermap.org/map/{layer}/{z}/{x}/{y}.png"

# OpenWeatherMap layer codes
OWM_LAYERS = {
    'temperature': 'temp_new',
    'rain':        'precipitation_new',
    'wind':        'wind_new',
    'clouds':      'clouds_new',
    'pressure':    'pressure_new',
}


def _tile_url(layer_key: str) -> str:
    """Build OWM tile URL template for Leaflet (API key injected client-side)."""
    code = OWM_LAYERS.get(layer_key, layer_key)
    return OWM_TILE_BASE.replace('{layer}', code)


def get_available_layers() -> dict:
    """
    Return configuration for all supported weather overlay layers.

    Each entry contains:
      - id            : internal identifier
      - name          : Vietnamese display name
      - name_en       : English label
      - icon          : Unicode icon
      - description   : Short description of the layer
      - unit          : Measurement unit
      - range         : Expected value range {min, max}
      - colors        : 3-stop gradient [cold/low, mid, hot/high]
      - legend_labels : Human-readable scale labels [low, mid, high]
      - tile_url      : OWM tile URL template (API key appended client-side)
      - owm_layer     : OWM layer code
      - default_opacity : Default fill opacity (0–1)
      - enabled_by_default : Whether layer is active on page load
      - category      : Grouping category
    """
    return {
        'temperature': {
            'id': 'temperature',
            'name': 'Nhiệt độ bề mặt',
            'name_en': 'Surface Temperature',
            'icon': '🌡️',
            'description': 'Nhiệt độ không khí tại độ cao 2m so với mặt đất.',
            'unit': '°C',
            'range': {'min': -20, 'max': 45},
            'colors': ['#2b83ba', '#ffffbf', '#d7191c'],
            'legend_labels': ['-20°C', '0°C', '15°C', '30°C', '45°C'],
            'tile_url': _tile_url('temperature'),
            'owm_layer': OWM_LAYERS['temperature'],
            'default_opacity': 0.7,
            'enabled_by_default': True,
            'category': 'atmosphere',
        },
        'rain': {
            'id': 'rain',
            'name': 'Lượng mưa',
            'name_en': 'Precipitation',
            'icon': '🌧️',
            'description': 'Tích lũy lượng mưa (mm) trong 3 giờ qua.',
            'unit': 'mm/3h',
            'range': {'min': 0, 'max': 140},
            'colors': ['#f0f9ff', '#38bdf8', '#1e3a8a'],
            'legend_labels': ['0', '20', '50', '100', '140+'],
            'tile_url': _tile_url('rain'),
            'owm_layer': OWM_LAYERS['rain'],
            'default_opacity': 0.75,
            'enabled_by_default': False,
            'category': 'precipitation',
        },
        'wind': {
            'id': 'wind',
            'name': 'Tốc độ gió',
            'name_en': 'Wind Speed',
            'icon': '💨',
            'description': 'Tốc độ gió ở độ cao 10m (thang Beaufort).',
            'unit': 'm/s',
            'range': {'min': 0, 'max': 50},
            'colors': ['#d1fae5', '#10b981', '#064e3b'],
            'legend_labels': ['Lặng', '5', '15', '30', '50+'],
            'tile_url': _tile_url('wind'),
            'owm_layer': OWM_LAYERS['wind'],
            'default_opacity': 0.7,
            'enabled_by_default': False,
            'category': 'atmosphere',
        },
        'clouds': {
            'id': 'clouds',
            'name': 'Độ che phủ mây',
            'name_en': 'Cloud Cover',
            'icon': '☁️',
            'description': 'Phần trăm bầu trời bị che phủ bởi mây.',
            'unit': '%',
            'range': {'min': 0, 'max': 100},
            'colors': ['#fefce8', '#cbd5e1', '#1e293b'],
            'legend_labels': ['0%', '25%', '50%', '75%', '100%'],
            'tile_url': _tile_url('clouds'),
            'owm_layer': OWM_LAYERS['clouds'],
            'default_opacity': 0.65,
            'enabled_by_default': False,
            'category': 'atmosphere',
        },
        'pressure': {
            'id': 'pressure',
            'name': 'Áp suất khí quyển',
            'name_en': 'Atmospheric Pressure',
            'icon': '📊',
            'description': 'Áp suất khí quyển tại mực nước biển (hPa).',
            'unit': 'hPa',
            'range': {'min': 940, 'max': 1060},
            'colors': ['#fde68a', '#f97316', '#7c3aed'],
            'legend_labels': ['940', '970', '1013', '1040', '1060'],
            'tile_url': _tile_url('pressure'),
            'owm_layer': OWM_LAYERS['pressure'],
            'default_opacity': 0.6,
            'enabled_by_default': False,
            'category': 'atmosphere',
        },
    }


def get_layer_by_id(layer_id: str) -> dict | None:
    """Return a single layer configuration by its ID, or None if not found."""
    return get_available_layers().get(layer_id)

