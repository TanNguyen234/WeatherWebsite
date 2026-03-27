from django.urls import path
from adminpanel.views import (
    DashboardView,
    UserListView,
    UserDetailView,
    UserToggleActiveView,
    LocationListView,
    RouteListView,
    LayerConfigView,
    APIHealthView,
    APIHealthCheckView,
)

app_name = 'adminpanel'

urlpatterns = [
    path('',                 DashboardView.as_view(),        name='dashboard'),
    path('users/',           UserListView.as_view(),          name='users'),
    path('users/<int:user_id>/', UserDetailView.as_view(),    name='user-detail'),
    path('users/toggle/', UserToggleActiveView.as_view(), name='user-toggle-active'),
    path('locations/',       LocationListView.as_view(),      name='locations'),
    path('routes/',          RouteListView.as_view(),         name='routes'),
    path('layers/',          LayerConfigView.as_view(),       name='layer-config'),
    path('api-health/',      APIHealthView.as_view(),         name='api-health'),
    path('api-health/check/',APIHealthCheckView.as_view(),    name='api-health-check'),
]
