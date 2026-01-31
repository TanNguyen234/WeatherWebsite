from django.urls import path
from . import views

urlpatterns = [
    path('compare/', views.CompareView.as_view(), name='compare'),
    path('route/', views.RouteView.as_view(), name='route'),
]
