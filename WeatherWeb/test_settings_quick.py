import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WeatherWeb.settings')
from django.conf import settings

print("GDAL_LIBRARY_PATH is:", getattr(settings, 'GDAL_LIBRARY_PATH', 'NOT_SET'))
print("GEOS_LIBRARY_PATH is:", getattr(settings, 'GEOS_LIBRARY_PATH', 'NOT_SET'))
