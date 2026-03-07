"""
Weather GIS – Domain Models
-----------------------------
Only spatial user-intent data is persisted here.
Weather/forecast data is NEVER stored – it is fetched on demand.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

class UserProfile(models.Model):
    """
    Extends Django's built-in User with GIS/application-level attributes.
    One-to-one with auth_user – created automatically on first save.
    """

    ROLE_USER  = 'user'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_USER,  'Người dùng'),
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
    bio = models.TextField(
        blank=True, default='',
        help_text='Giới thiệu ngắn về người dùng',
    )
    avatar_url = models.URLField(
        max_length=500, blank=True, default='',
        help_text='URL ảnh đại diện (tuỳ chọn)',
    )
    default_latitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text='Vĩ độ trung tâm mặc định khi mở bản đồ',
    )
    default_longitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text='Kinh độ trung tâm mặc định khi mở bản đồ',
    )
    default_zoom = models.SmallIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(18)],
        help_text='Mức zoom mặc định (1–18)',
    )
    # User-preference toggles (used by layer UI)
    show_temperature = models.BooleanField(default=True)
    show_rain        = models.BooleanField(default=True)
    show_wind        = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile'
        verbose_name        = 'Hồ sơ người dùng'
        verbose_name_plural = 'Hồ sơ người dùng'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_admin_role(self):
        """True when the profile role == admin (separate from is_staff)."""
        return self.role == self.ROLE_ADMIN

    @classmethod
    def get_or_create_for_user(cls, user):
        """Return the profile, creating it if it does not yet exist."""
        profile, _ = cls.objects.get_or_create(
            user=user,
            defaults={'role': cls.ROLE_ADMIN if user.is_staff else cls.ROLE_USER},
        )
        return profile


# ---------------------------------------------------------------------------
# UserLocation
# ---------------------------------------------------------------------------

class UserLocation(models.Model):
    """
    A geographic point saved by a user.
    Lat/lng are DOUBLE PRECISION to support exact PostGIS migration later.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='locations',
    )
    name = models.CharField(
        max_length=255, null=True, blank=True,
        help_text='Tên hiển thị tuỳ chọn (vd: "Văn phòng HN")',
    )
    description = models.TextField(
        blank=True, default='',
        help_text='Ghi chú chi tiết về địa điểm',
    )
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text='Vĩ độ, phạm vi [-90, 90]',
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text='Kinh độ, phạm vi [-180, 180]',
    )
    # Lưu địa chỉ ngược (reverse-geocoded) để hiển thị nhanh trên UI
    address = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Địa chỉ tham chiếu (reverse-geocoded, không bắt buộc)',
    )
    is_favourite = models.BooleanField(
        default=False,
        help_text='Đánh dấu địa điểm yêu thích',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_location'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='idx_user_location_lat_lng'),
            models.Index(fields=['user', 'is_favourite'],  name='idx_user_location_user_fav'),
        ]
        verbose_name        = 'Địa điểm'
        verbose_name_plural = 'Địa điểm'

    def __str__(self):
        return self.name or f'({self.latitude:.4f}, {self.longitude:.4f})'


# ---------------------------------------------------------------------------
# Area  (circular analysis zone)
# ---------------------------------------------------------------------------

class Area(models.Model):
    """
    A circular spatial analysis zone centred on a UserLocation.
    Future PostGIS upgrade: replace (center + radius_km) with ST_Buffer POINT.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='areas',
    )
    name = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Tên vùng phân tích',
    )
    center = models.ForeignKey(
        UserLocation,
        on_delete=models.CASCADE,
        db_column='center_location_id',
        related_name='areas',
        help_text='Tâm của vùng phân tích',
    )
    radius_km = models.FloatField(
        validators=[MinValueValidator(0.1), MaxValueValidator(500)],
        help_text='Bán kính (km), phạm vi [0.1, 500]',
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'area'
        verbose_name        = 'Vùng phân tích'
        verbose_name_plural = 'Vùng phân tích'

    def __str__(self):
        return self.name or f'Vùng {self.radius_km} km quanh {self.center}'


# ---------------------------------------------------------------------------
# LocationGroup  &  LocationGroupItem
# ---------------------------------------------------------------------------

class LocationGroup(models.Model):
    """
    A named collection of UserLocations belonging to one user.
    Used for grouping related points on the map (e.g. "Công trình miền Bắc").
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='location_groups',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    # Hex colour for map icon / sidebar badge  (e.g. "#3b82f6")
    color = models.CharField(
        max_length=7, blank=True, default='#3b82f6',
        help_text='Màu nhóm (hex, vd: #3b82f6)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'location_group'
        verbose_name        = 'Nhóm địa điểm'
        verbose_name_plural = 'Nhóm địa điểm'

    def __str__(self):
        return f'{self.name} ({self.user.username})'


class LocationGroupItem(models.Model):
    """Junction between LocationGroup and UserLocation."""

    group = models.ForeignKey(
        LocationGroup,
        on_delete=models.CASCADE,
        db_column='group_id',
        related_name='items',
    )
    location = models.ForeignKey(
        UserLocation,
        on_delete=models.CASCADE,
        db_column='location_id',
        related_name='group_memberships',
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table   = 'location_group_item'
        unique_together = ('group', 'location')
        ordering        = ['display_order']
        verbose_name        = 'Thành viên nhóm'
        verbose_name_plural = 'Thành viên nhóm'

    def __str__(self):
        return f'{self.location} → {self.group}'


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

class Route(models.Model):
    """
    A directional path between two UserLocations.
    Future PostGIS upgrade: replace (start + end) with LINESTRING SRID 4326.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='routes',
    )
    name = models.CharField(
        max_length=255,
        help_text='Tên tuyến đường hiển thị trên UI',
    )
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
    distance_km = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text='Khoảng cách đường bộ (km), điền sau khi gọi OSRM',
    )
    duration_minutes = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text='Thời gian di chuyển ước tính (phút)',
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'route'
        ordering = ['-created_at']
        verbose_name        = 'Tuyến đường'
        verbose_name_plural = 'Tuyến đường'

    def __str__(self):
        return f'{self.name}: {self.start_location} → {self.end_location}'


# ---------------------------------------------------------------------------
# InteractionLog  (optional analytics)
# ---------------------------------------------------------------------------

class InteractionLog(models.Model):
    """
    Lightweight audit/analytics log.
    Stores WHAT happened, not weather data.
    """

    ACTION_MAP_CLICK   = 'map_click'
    ACTION_SAVE_LOC    = 'save_location'
    ACTION_SAVE_ROUTE  = 'save_route'
    ACTION_ANALYZE     = 'analyze_area'
    ACTION_LOGIN       = 'login'
    ACTION_REGISTER    = 'register'
    ACTION_CHOICES = [
        (ACTION_MAP_CLICK,  'Click bản đồ'),
        (ACTION_SAVE_LOC,   'Lưu địa điểm'),
        (ACTION_SAVE_ROUTE, 'Lưu tuyến đường'),
        (ACTION_ANALYZE,    'Phân tích vùng'),
        (ACTION_LOGIN,      'Đăng nhập'),
        (ACTION_REGISTER,   'Đăng ký'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='user_id',
        related_name='interaction_logs',
    )
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
    )
    # Optional context: e.g. lat/lng of the click, location id saved etc.
    detail = models.JSONField(
        null=True, blank=True,
        help_text='Chi tiết bổ sung dạng JSON (không chứa dữ liệu thời tiết)',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'interaction_log'
        ordering = ['-created_at']
        verbose_name        = 'Nhật ký tương tác'
        verbose_name_plural = 'Nhật ký tương tác'

    def __str__(self):
        who = self.user.username if self.user else 'anonymous'
        return f'[{self.action_type}] {who} @ {self.created_at:%Y-%m-%d %H:%M}'