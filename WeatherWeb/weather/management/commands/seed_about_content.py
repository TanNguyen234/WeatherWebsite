"""
Management command: seed_about_content
Populates the AboutContent table with the original hardcoded About page content.
Safe to run multiple times — skips existing keys.

Usage:
    python manage.py seed_about_content
"""
from django.core.management.base import BaseCommand
from weather.models import AboutContent

INITIAL_BLOCKS = [
    {
        'key':   'he_thong',
        'title': 'H\u1ec7 th\u1ed1ng n\u00e0y d\u00f9ng \u0111\u1ec3 l\u00e0m g\u00ec?',
        'body': (
            'WeatherGIS gi\u00fap b\u1ea1n l\u00e0m vi\u1ec7c v\u1edbi d\u1eef li\u1ec7u \u0111\u1ecba l\u00fd ngay tr\u00ean b\u1ea3n \u0111\u1ed3:\n'
            'Xem v\u1ecb tr\u00ed tr\u1ef1c ti\u1ebfp theo t\u1ecda \u0111\u1ed9 tr\u00ean b\u1ea3n \u0111\u1ed3.\n'
            'L\u01b0u c\u00e1c \u0111i\u1ec3m quan tr\u1ecdng \u0111\u1ec3 d\u00f9ng l\u1ea1i khi c\u1ea7n.\n'
            'Theo d\u00f5i tuy\u1ebfn \u0111\u01b0\u1eddng gi\u1eefa hai \u0111\u1ecba \u0111i\u1ec3m.\n'
            'So s\u00e1nh th\u00f4ng tin theo t\u1eebng khu v\u1ef1c \u0111\u1ec3 h\u1ed7 tr\u1ee3 ra quy\u1ebft \u0111\u1ecbnh.'
        ),
        'order': 0,
    },
    {
        'key':   'loi_ich',
        'title': 'L\u1ee3i \u00edch d\u00e0nh cho ng\u01b0\u1eddi d\u00f9ng',
        'body': (
            'N\u1eafm th\u00f4ng tin nhanh: Xem d\u1eef li\u1ec7u tr\u1ef1c quan tr\u00ean b\u1ea3n \u0111\u1ed3 \u0111\u1ec3 hi\u1ec3u khu v\u1ef1c b\u1ea1n quan t\u00e2m ch\u1ec9 trong v\u00e0i b\u01b0\u1edbc.\n'
            'D\u1ec5 theo d\u00f5i: L\u01b0u l\u1ea1i c\u00e1c \u0111\u1ecba \u0111i\u1ec3m th\u01b0\u1eddng d\u00f9ng \u0111\u1ec3 ti\u1ebft ki\u1ec7m th\u1eddi gian cho l\u1ea7n truy c\u1eadp sau.\n'
            'H\u1ed7 tr\u1ee3 quy\u1ebft \u0111\u1ecbnh: So s\u00e1nh th\u00f4ng tin gi\u1eefa c\u00e1c \u0111i\u1ec3m gi\u00fap b\u1ea1n ch\u1ecdn ph\u01b0\u01a1ng \u00e1n ph\u00f9 h\u1ee3p h\u01a1n.\n'
            'Th\u00e2n thi\u1ec7n v\u1edbi m\u1ecdi ng\u01b0\u1eddi: Giao di\u1ec7n \u0111\u01a1n gi\u1ea3n, kh\u00f4ng c\u1ea7n ki\u1ebfn th\u1ee9c chuy\u00ean s\u00e2u v\u1eabn c\u00f3 th\u1ec3 s\u1eed d\u1ee5ng hi\u1ec7u qu\u1ea3.'
        ),
        'order': 1,
    },
    {
        'key':   'chuc_nang',
        'title': 'B\u1ea1n c\u00f3 th\u1ec3 l\u00e0m g\u00ec tr\u00ean h\u1ec7 th\u1ed1ng?',
        'body': (
            'Kh\u00e1m ph\u00e1 b\u1ea3n \u0111\u1ed3 v\u00e0 ch\u1ecdn \u0111\u00fang v\u1ecb tr\u00ed c\u1ea7n theo d\u00f5i.\n'
            'L\u01b0u \u0111\u1ecba \u0111i\u1ec3m c\u00e1 nh\u00e2n \u0111\u1ec3 qu\u1ea3n l\u00fd d\u1eef li\u1ec7u g\u1ecdn g\u00e0ng.\n'
            'Xem v\u00e0 so s\u00e1nh th\u00f4ng tin gi\u1eefa nhi\u1ec1u \u0111i\u1ec3m \u0111\u1ecba l\u00fd kh\u00e1c nhau.\n'
            'Quan s\u00e1t tuy\u1ebfn \u0111\u01b0\u1eddng gi\u1eefa c\u00e1c v\u1ecb tr\u00ed \u0111\u1ec3 ph\u1ee5c v\u1ee5 k\u1ebf ho\u1ea1ch di chuy\u1ec3n.\n'
            'M\u1ee5c ti\u00eau c\u1ee7a WeatherGIS l\u00e0 gi\u00fap b\u1ea1n hi\u1ec3u d\u1eef li\u1ec7u \u0111\u1ecba l\u00fd nhanh h\u01a1n, r\u00f5 r\u00e0ng '
            'h\u01a1n v\u00e0 d\u1ec5 \u1ee9ng d\u1ee5ng trong c\u00f4ng vi\u1ec7c h\u1eb1ng ng\u00e0y.'
        ),
        'order': 2,
    },
]


class Command(BaseCommand):
    help = 'Seed the AboutContent table with the original hardcoded About page content.'

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for block in INITIAL_BLOCKS:
            _, was_created = AboutContent.objects.get_or_create(
                key=block['key'],
                defaults={
                    'title':      block['title'],
                    'body':       block['body'],
                    'order':      block['order'],
                    'is_visible': True,
                },
            )
            if was_created:
                self.stdout.write(self.style.SUCCESS(f"  [OK] Created: {block['key']}"))
                created += 1
            else:
                self.stdout.write(f"  [SKIP] Already exists: {block['key']}")
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Created: {created}, Skipped: {skipped}.'
            )
        )
