import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WeatherWeb.settings')
import django
django.setup()
from django.conf import settings
print("GDAL_LIBRARY_PATH:", getattr(settings, 'GDAL_LIBRARY_PATH', 'NOT SET'))
