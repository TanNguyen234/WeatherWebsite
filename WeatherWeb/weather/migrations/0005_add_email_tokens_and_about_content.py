# Hand-edited migration: only creates the 3 new models.
# The old model removals (Area, LocationGroup, etc.) and field cleanups are
# removed because those tables/columns don't exist in this DB.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weather', '0004_ensure_auth_user_email'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── AboutContent ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='AboutContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(
                    help_text='Định danh duy nhất (slug), ví dụ: main_intro, section_why',
                    max_length=100, unique=True,
                )),
                ('title', models.CharField(max_length=255, verbose_name='Tiêu đề')),
                ('body', models.TextField(blank=True, verbose_name='Nội dung')),
                ('order', models.PositiveSmallIntegerField(default=0, verbose_name='Thứ tự hiển thị')),
                ('is_visible', models.BooleanField(default=True, verbose_name='Hiển thị')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='about_edits',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Chỉnh sửa bởi',
                )),
            ],
            options={
                'verbose_name': 'Nội dung trang Giới thiệu',
                'verbose_name_plural': 'Nội dung trang Giới thiệu',
                'db_table': 'about_content',
                'ordering': ['order', 'key'],
            },
        ),

        # ── EmailChangeToken ──────────────────────────────────────────────
        migrations.CreateModel(
            name='EmailChangeToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('new_email', models.EmailField(max_length=254, verbose_name='Email mới chờ xác nhận')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    db_column='user_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='email_change_token',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Token đổi email',
                'verbose_name_plural': 'Token đổi email',
                'db_table': 'email_change_token',
            },
        ),

        # ── EmailVerificationToken ────────────────────────────────────────
        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    db_column='user_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='email_token',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Token xác thực email',
                'verbose_name_plural': 'Token xác thực email',
                'db_table': 'email_verification_token',
            },
        ),
    ]
