import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WeatherWeb.settings')
django.setup()

from weather.utils.visualize import generate_prediction_chart_png, png_to_base64

def test_chart():
    rows = [
        {"timestamp": "2026-04-16T12:00", "api_temperature": 33.1, "ai_temperature": 33.4},
        {"timestamp": "2026-04-16T13:00", "api_temperature": 33.2, "ai_temperature": 33.5},
    ]
    try:
        png_bytes = generate_prediction_chart_png(rows, metric="temperature")
        b64 = png_to_base64(png_bytes)
        print(f"Success! Base64 length: {len(b64)}")
        print(f"Starts with: {b64[:30]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chart()
