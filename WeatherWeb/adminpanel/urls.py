from django.urls import path
from adminpanel.views import (
    DashboardView,
    UserListView,
    UserDetailView,
    UserToggleActiveView,
    UserEditView,
    UserRoleUpdateView,
    LocationListView,
    RouteListView,
    LayerConfigView,
    APIHealthView,
    APIHealthCheckView,
    AboutContentListView,
    AboutContentCreateView,
    AboutContentEditView,
    AboutContentDeleteView,
    AboutContentReorderView,
)

app_name = 'adminpanel'

urlpatterns = [
    # Dashboard & Profile
    path('',                    DashboardView.as_view(),        name='dashboard'),

    # Users
    path('users/',              UserListView.as_view(),          name='users'),
    path('users/<int:user_id>/',         UserDetailView.as_view(),    name='user-detail'),
    path('users/toggle/',       UserToggleActiveView.as_view(), name='user-toggle-active'),
    path('users/<int:user_id>/edit/',    UserEditView.as_view(),      name='user-edit'),
    path('users/<int:user_id>/role/',    UserRoleUpdateView.as_view(),name='user-role-update'),

    # Locations & Routes
    path('locations/',          LocationListView.as_view(),      name='locations'),
    path('routes/',             RouteListView.as_view(),         name='routes'),

    # Layers
    path('layers/',             LayerConfigView.as_view(),       name='layer-config'),

    # API Health
    path('api-health/',         APIHealthView.as_view(),         name='api-health'),
    path('api-health/check/',   APIHealthCheckView.as_view(),    name='api-health-check'),

    # About CMS
    path('about/',              AboutContentListView.as_view(),  name='about-content'),
    path('about/create/',       AboutContentCreateView.as_view(),name='about-content-create'),
    path('about/<int:pk>/edit/',AboutContentEditView.as_view(),  name='about-content-edit'),
    path('about/<int:pk>/delete/', AboutContentDeleteView.as_view(), name='about-content-delete'),
    path('about/reorder/',      AboutContentReorderView.as_view(),name='about-content-reorder'),
]
