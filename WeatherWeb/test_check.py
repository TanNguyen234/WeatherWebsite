import os
import sys
import traceback
try:
    from django.core.management import execute_from_command_line
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WeatherWeb.settings')
    execute_from_command_line(['manage.py', 'check'])
except Exception as e:
    with open('check_output.txt', 'w') as f:
        traceback.print_exc(file=f)
