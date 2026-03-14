"""
Weather GIS – Domain Models
Only actively used user-intent spatial entities are persisted.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UserProfile(models.Model):
    ROLE_USER = 'user'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_USER, 'Người dùng'),
        (ROLE_ADMIN, 'Quản trị viên'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        db_column='user_id',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_USER,
        help_text='Vai trò trong hệ thống (user / admin)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile'
        verbose_name = 'Hồ sơ người dùng'
        verbose_name_plural = 'Hồ sơ người dùng'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class UserLocation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='locations',
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_location'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='idx_user_location_lat_lng'),
        ]
        verbose_name = 'Địa điểm'
        verbose_name_plural = 'Địa điểm'

    def __str__(self):
        return self.name or f'({self.latitude:.4f}, {self.longitude:.4f})'


class Route(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='routes',
    )
    name = models.CharField(max_length=255)
    start_location = models.ForeignKey(
        UserLocation,
        on_delete=models.CASCADE,
        db_column='start_location_id',
        related_name='routes_start',
    )
    end_location = models.ForeignKey(
        UserLocation,
        on_delete=models.CASCADE,
        db_column='end_location_id',
        related_name='routes_end',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'route'
        ordering = ['-created_at']
        verbose_name = 'Tuyến đường'
        verbose_name_plural = 'Tuyến đường'

    def __str__(self):
        return f'{self.name}: {self.start_location} → {self.end_location}'