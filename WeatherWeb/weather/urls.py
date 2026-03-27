from django.urls import path
from django.contrib.auth import views as auth_views
from weather.views.map import MapView
from weather.views.predict import PredictView
from weather.views.compare import CompareView
from weather.views.route import RouteView
from weather.views.layers import LayersView
from weather.views.about import AboutView
from weather.views.auth import LoginView, RegisterView, LogoutView
from weather.views.api import (
    WeatherAPIView,
    LocationAPIView,
    LocationDetailAPIView,
    CompareAPIView,
    RouteAPIView,
    RouteCreateAPIView,
    PredictAPIView,
    PredictExportCSVView,
    PredictExportImageView,
    LayerConfigAPIView,
    LayerPointDataAPIView,
    GeocodeProxyView,
    RouteGeometryProxyView,
)

urlpatterns = [
    # Page views
    path('', MapView.as_view(), name='map'),
    path('predict/', PredictView.as_view(), name='predict'),
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
    path('api/predict/', PredictAPIView.as_view(), name='api-predict'),
    path('predict/export/csv/', PredictExportCSVView.as_view(), name='predict-export-csv'),
    path('predict/export/image/', PredictExportImageView.as_view(), name='predict-export-image'),
    path('api/locations/', LocationAPIView.as_view(), name='api-locations'),
    path('api/locations/<int:location_id>/', LocationDetailAPIView.as_view(), name='api-location-detail'),
    path('api/compare/', CompareAPIView.as_view(), name='api-compare'),
    path('api/route/', RouteAPIView.as_view(), name='api-route'),
    path('api/routes/', RouteCreateAPIView.as_view(), name='api-routes'),

    # Layer API
    path('api/layers/', LayerConfigAPIView.as_view(), name='api-layer-config'),
    path('api/layers/points/', LayerPointDataAPIView.as_view(), name='api-layer-points'),

    # Third-party proxies (server-side geocoding + routing)
    path('api/geocode/', GeocodeProxyView.as_view(), name='api-geocode'),
    path('api/route-geometry/', RouteGeometryProxyView.as_view(), name='api-route-geometry'),

    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
]
