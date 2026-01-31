from django.urls import path
from weather.views.map import MapView
from weather.views.forecast import ForecastView
from weather.views.api import WeatherAPIView

urlpatterns = [
    path('forecast/', ForecastView.as_view(), name='forecast'),
    path('', MapView.as_view(), name='map'),
    path('api/weather/', WeatherAPIView.as_view(), name='weather-api'),
]