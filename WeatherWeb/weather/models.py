"""
Weather GIS – Domain Models
Only actively used user-intent spatial entities are persisted.
"""

import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

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


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

class EmailVerificationToken(models.Model):
    """
    One-time token used to activate a newly registered account.
    Expires after TOKEN_EXPIRY_HOURS hours.
    """
    TOKEN_EXPIRY_HOURS = 24

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='email_token',
        db_column='user_id',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_verification_token'
        verbose_name = 'Token xác thực email'
        verbose_name_plural = 'Token xác thực email'

    def is_expired(self):
        expiry = self.created_at + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        return timezone.now() > expiry

    def __str__(self):
        return f'Token cho {self.user.username} (hết hạn: {self.TOKEN_EXPIRY_HOURS}h)'


# ---------------------------------------------------------------------------
# Email Change Token
# ---------------------------------------------------------------------------

class EmailChangeTokenManager(models.Manager):
    def create_for_user(self, user, new_email):
        """Delete any existing change token for user and create a fresh one."""
        self.filter(user=user).delete()
        return self.create(user=user, new_email=new_email)


class EmailChangeToken(models.Model):
    """
    Temporary token that holds a requested new email address.
    The user.email is only updated after clicking the confirmation link sent
    to the NEW address.
    """
    TOKEN_EXPIRY_HOURS = 24

    objects = EmailChangeTokenManager()

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='email_change_token',
        db_column='user_id',
    )
    new_email = models.EmailField(verbose_name='Email mới chờ xác nhận')
    token     = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_change_token'
        verbose_name = 'Token đổi email'
        verbose_name_plural = 'Token đổi email'

    def is_expired(self):
        expiry = self.created_at + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        return timezone.now() > expiry

    def __str__(self):
        return f'Đổi email → {self.new_email} cho {self.user.username}'


# ---------------------------------------------------------------------------
# About Page CMS
# ---------------------------------------------------------------------------

class AboutContent(models.Model):
    """
    Editable content block for the About page.
    Admin manages these via the custom panel; the about view renders them dynamically.
    """
    key = models.SlugField(
        max_length=100,
        unique=True,
        help_text='Định danh duy nhất (slug), ví dụ: main_intro, section_why',
    )
    title = models.CharField(max_length=255, verbose_name='Tiêu đề')
    body = models.TextField(verbose_name='Nội dung', blank=True)
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Thứ tự hiển thị')
    is_visible = models.BooleanField(default=True, verbose_name='Hiển thị')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='about_edits',
        verbose_name='Chỉnh sửa bởi',
    )

    class Meta:
        db_table = 'about_content'
        ordering = ['order', 'key']
        verbose_name = 'Nội dung trang Giới thiệu'
        verbose_name_plural = 'Nội dung trang Giới thiệu'

    def __str__(self):
        return f'[{self.order}] {self.title}'