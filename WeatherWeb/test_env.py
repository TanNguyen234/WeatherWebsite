import os
from dotenv import load_dotenv

load_dotenv()
print("OSGEO_PATH:", os.environ.get('OSGEO_PATH'))
print("VIRTUAL_ENV:", os.environ.get('VIRTUAL_ENV'))
