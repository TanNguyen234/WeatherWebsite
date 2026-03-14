from django.contrib import admin
from .models import UserProfile, UserLocation, Route

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'created_at')
    list_filter   = ('role',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('role',)
    ordering = ('-created_at',)

    fieldsets = (
        ('Tài khoản', {
            'fields': ('user', 'role'),
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display  = ('name', 'user', 'lat_lng', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_select_related = ('user',)

    @admin.display(description='Toạ độ')
    def lat_lng(self, obj):
        return f'{obj.latitude:.5f}, {obj.longitude:.5f}'

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display  = ('name', 'user', 'start_location', 'end_location', 'created_at')
    search_fields = ('name', 'user__username', 'start_location__name', 'end_location__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_select_related = ('user', 'start_location', 'end_location')

    fieldsets = (
        ('Thông tin tuyến', {
            'fields': ('user', 'name', 'start_location', 'end_location'),
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
