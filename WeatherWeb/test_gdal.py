import traceback
import os
import sys

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WeatherWeb.settings')
    from WeatherWeb import settings
    print("Settings loaded successfully!")
    print("GDAL_LIBRARY_PATH:", settings.GDAL_LIBRARY_PATH)
    import ctypes
    print("Trying to load GDAL...")
    ctypes.CDLL(settings.GDAL_LIBRARY_PATH)
    print("GDAL Loaded via ctypes!")
except Exception as e:
    with open("test_gdal_error.txt", "w", encoding='utf-8') as f:
        f.write(traceback.format_exc())
    print("Error occurred, wrote traceback to test_gdal_error.txt")
