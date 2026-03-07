"""
weather/admin.py – Django Admin registration for all Weather GIS models.

Customised list displays, filters, and search fields to give admin staff
full visibility into spatial data without direct SQL access.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    UserProfile,
    UserLocation,
    Area,
    LocationGroup,
    LocationGroupItem,
    Route,
    InteractionLog,
)


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'bio_short', 'show_temperature', 'show_wind', 'created_at')
    list_filter   = ('role', 'show_temperature', 'show_rain', 'show_wind')
    search_fields = ('user__username', 'user__email', 'bio')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('role',)
    ordering = ('-created_at',)

    fieldsets = (
        ('Tài khoản', {
            'fields': ('user', 'role'),
        }),
        ('Thông tin cá nhân', {
            'fields': ('bio', 'avatar_url'),
        }),
        ('Tuỳ chọn bản đồ', {
            'fields': ('default_latitude', 'default_longitude', 'default_zoom'),
        }),
        ('Tuỳ chọn lớp thời tiết', {
            'fields': ('show_temperature', 'show_rain', 'show_wind'),
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Bio')
    def bio_short(self, obj):
        return obj.bio[:60] + '…' if len(obj.bio) > 60 else obj.bio


# ---------------------------------------------------------------------------
# UserLocation
# ---------------------------------------------------------------------------

@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display  = ('name', 'user', 'lat_lng', 'address_short', 'is_favourite', 'created_at')
    list_filter   = ('is_favourite', 'created_at')
    search_fields = ('name', 'description', 'address', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    list_select_related = ('user',)

    @admin.display(description='Toạ độ')
    def lat_lng(self, obj):
        return f'{obj.latitude:.5f}, {obj.longitude:.5f}'

    @admin.display(description='Địa chỉ')
    def address_short(self, obj):
        return obj.address[:60] + '…' if len(obj.address) > 60 else (obj.address or '–')


# ---------------------------------------------------------------------------
# Area
# ---------------------------------------------------------------------------

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display  = ('name', 'user', 'center', 'radius_km', 'created_at')
    search_fields = ('name', 'user__username', 'center__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_select_related = ('user', 'center')


# ---------------------------------------------------------------------------
# LocationGroup  &  LocationGroupItem  (inline)
# ---------------------------------------------------------------------------

class LocationGroupItemInline(admin.TabularInline):
    model  = LocationGroupItem
    extra  = 1
    fields = ('location', 'display_order')
    autocomplete_fields = ('location',)


@admin.register(LocationGroup)
class LocationGroupAdmin(admin.ModelAdmin):
    list_display  = ('name', 'user', 'color_badge', 'item_count', 'created_at')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    inlines  = [LocationGroupItemInline]
    list_select_related = ('user',)

    @admin.display(description='Màu')
    def color_badge(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:3px;background:{};border:1px solid #ccc"></span> {}',
            obj.color, obj.color,
        )

    @admin.display(description='Số điểm')
    def item_count(self, obj):
        return obj.items.count()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display  = ('name', 'user', 'start_location', 'end_location',
                     'distance_km', 'duration_minutes', 'created_at')
    search_fields = ('name', 'user__username', 'start_location__name', 'end_location__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    list_select_related = ('user', 'start_location', 'end_location')

    fieldsets = (
        ('Thông tin tuyến', {
            'fields': ('user', 'name', 'start_location', 'end_location'),
        }),
        ('Số liệu OSRM', {
            'fields': ('distance_km', 'duration_minutes', 'notes'),
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


# ---------------------------------------------------------------------------
# InteractionLog  (read-only)
# ---------------------------------------------------------------------------

@admin.register(InteractionLog)
class InteractionLogAdmin(admin.ModelAdmin):
    list_display  = ('action_type', 'user', 'ip_address', 'detail_short', 'created_at')
    list_filter   = ('action_type', 'created_at')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'action_type', 'detail', 'ip_address', 'created_at')
    ordering = ('-created_at',)
    list_select_related = ('user',)

    # Prevent creating or deleting logs from admin
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description='Chi tiết')
    def detail_short(self, obj):
        if obj.detail:
            text = str(obj.detail)
            return text[:80] + '…' if len(text) > 80 else text
        return '–'
