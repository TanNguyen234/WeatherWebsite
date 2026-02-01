from django.urls import path
from weather.views.map import MapView
from weather.views.forecast import ForecastView
from weather.views.compare import CompareView
from weather.views.route import RouteView
from weather.views.layers import LayersView
from weather.views.about import AboutView
from weather.views.auth import LoginView, RegisterView, LogoutView
from weather.views.api import (
    WeatherAPIView,
    LocationAPIView,
    LocationDetailAPIView,
    ForecastAPIView,
    CompareAPIView,
    RouteAPIView,
    RouteCreateAPIView
)

urlpatterns = [
    # Page views
    path('', MapView.as_view(), name='map'),
    path('forecast/', ForecastView.as_view(), name='forecast'),
    path('compare/', CompareView.as_view(), name='compare'),
    path('route/', RouteView.as_view(), name='route'),
    path('layers/', LayersView.as_view(), name='layers'),
    path('about/', AboutView.as_view(), name='about'),
    
    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # API endpoints
    path('api/weather/', WeatherAPIView.as_view(), name='api-weather'),
    path('api/locations/', LocationAPIView.as_view(), name='api-locations'),
    path('api/locations/<int:location_id>/', LocationDetailAPIView.as_view(), name='api-location-detail'),
    path('api/forecast/', ForecastAPIView.as_view(), name='api-forecast'),
    path('api/compare/', CompareAPIView.as_view(), name='api-compare'),
    path('api/route/', RouteAPIView.as_view(), name='api-route'),
    path('api/routes/', RouteCreateAPIView.as_view(), name='api-routes'),
]