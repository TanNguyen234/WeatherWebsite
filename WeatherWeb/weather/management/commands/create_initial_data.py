"""
management/commands/create_initial_data.py

Creates initial database seed data:
  - Superuser  admin   (password: admin123)   → profile role: admin
  - Regular user testuser (password: user123) → profile role: user
  - Sample locations attached to testuser

Usage:
    python manage.py create_initial_data
    python manage.py create_initial_data --reset   # drops & recreates both accounts
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from weather.models import UserProfile, UserLocation

User = get_user_model()

# ── Seed definitions ────────────────────────────────────────────────────────

ADMIN_ACCOUNT = {
    'username':  'admin',
    'password':  'admin123',
    'email':     'admin@weathergis.local',
    'is_staff':  True,
    'is_superuser': True,
    'first_name': 'Admin',
    'last_name':  'WeatherGIS',
}

USER_ACCOUNT = {
    'username':  'testuser',
    'password':  'user123',
    'email':     'testuser@weathergis.local',
    'is_staff':  False,
    'is_superuser': False,
    'first_name': 'Test',
    'last_name':  'User',
}

SAMPLE_LOCATIONS = [
    {
        'name': 'Hà Nội – Hoàn Kiếm',
        'latitude':  21.0285,
        'longitude': 105.8542,
        'address': 'Hoàn Kiếm, Hà Nội, Việt Nam',
        'description': 'Trung tâm thành phố Hà Nội',
        'is_favourite': True,
    },
    {
        'name': 'TP. Hồ Chí Minh – Bến Thành',
        'latitude':  10.7769,
        'longitude': 106.7009,
        'address': 'Quận 1, TP. Hồ Chí Minh, Việt Nam',
        'description': 'Trung tâm TP. HCM',
        'is_favourite': True,
    },
    {
        'name': 'Đà Nẵng – Sơn Trà',
        'latitude':  16.0544,
        'longitude': 108.2022,
        'address': 'Đà Nẵng, Việt Nam',
        'description': 'Bán đảo Sơn Trà, Đà Nẵng',
        'is_favourite': False,
    },
]


class Command(BaseCommand):
    help = 'Seed the database with initial admin and user accounts + sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete and recreate the seed accounts before inserting',
        )

    def handle(self, *args, **options):
        reset = options['reset']

        # ── Admin account ────────────────────────────────────────────────────
        admin_user = self._upsert_user(ADMIN_ACCOUNT, reset=reset)
        self._upsert_profile(admin_user, role=UserProfile.ROLE_ADMIN, bio='Quản trị viên hệ thống WeatherGIS')
        self.stdout.write(self.style.SUCCESS(f'  ✓ Admin  : {admin_user.username} / admin123'))

        # ── Regular user ─────────────────────────────────────────────────────
        test_user = self._upsert_user(USER_ACCOUNT, reset=reset)
        self._upsert_profile(test_user, role=UserProfile.ROLE_USER, bio='Người dùng thử nghiệm')
        self.stdout.write(self.style.SUCCESS(f'  ✓ User   : {test_user.username} / user123'))

        # ── Sample locations for testuser ─────────────────────────────────────
        loc_count = 0
        for loc_data in SAMPLE_LOCATIONS:
            _, created = UserLocation.objects.get_or_create(
                user=test_user,
                latitude=loc_data['latitude'],
                longitude=loc_data['longitude'],
                defaults={
                    'name':        loc_data['name'],
                    'address':     loc_data['address'],
                    'description': loc_data['description'],
                    'is_favourite': loc_data['is_favourite'],
                },
            )
            if created:
                loc_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Locations: {loc_count} mới (bỏ qua {len(SAMPLE_LOCATIONS) - loc_count} đã có)'
        ))
        self.stdout.write(self.style.SUCCESS('\nDone – dữ liệu khởi tạo đã sẵn sàng.'))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _upsert_user(self, spec, reset=False):
        """Create or update a user from a spec dict."""
        username = spec['username']
        if reset:
            User.objects.filter(username=username).delete()

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email':        spec['email'],
                'first_name':   spec.get('first_name', ''),
                'last_name':    spec.get('last_name', ''),
                'is_staff':     spec.get('is_staff', False),
                'is_superuser': spec.get('is_superuser', False),
                'is_active':    True,
            },
        )
        if created:
            user.set_password(spec['password'])
            user.save(update_fields=['password'])
        else:
            # Ensure the password and flags are correct even if user already existed
            changed = []
            if not user.check_password(spec['password']):
                user.set_password(spec['password'])
                changed.append('password')
            for field in ('is_staff', 'is_superuser', 'is_active'):
                if getattr(user, field) != spec.get(field, False):
                    setattr(user, field, spec.get(field, False))
                    changed.append(field)
            if changed:
                user.save(update_fields=changed)
        return user

    def _upsert_profile(self, user, role, bio=''):
        """Create or update the UserProfile for a user."""
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role':           role,
                'bio':            bio,
                'default_zoom':   6,
                'show_temperature': True,
                'show_rain':      True,
                'show_wind':      False,
            },
        )
        if not created and profile.role != role:
            profile.role = role
            profile.save(update_fields=['role'])
        return profile
