from django.db import migrations


ENSURE_AUTH_USER_EMAIL_SQL = """
ALTER TABLE IF EXISTS auth_user
    ADD COLUMN IF NOT EXISTS email VARCHAR(254) NOT NULL DEFAULT '';
"""


class Migration(migrations.Migration):

    dependencies = [
        ("weather", "0003_cleanup_unused_schema"),
    ]

    operations = [
        migrations.RunSQL(
            sql=ENSURE_AUTH_USER_EMAIL_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
