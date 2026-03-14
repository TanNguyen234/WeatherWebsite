from django.db import migrations


DROP_UNUSED_TABLES_SQL = """
DROP TABLE IF EXISTS location_group_item CASCADE;
DROP TABLE IF EXISTS location_group CASCADE;
DROP TABLE IF EXISTS area CASCADE;
DROP TABLE IF EXISTS interaction_log CASCADE;
"""

DROP_UNUSED_COLUMNS_SQL = """
DROP INDEX IF EXISTS idx_user_location_user_fav;

ALTER TABLE IF EXISTS user_location
    DROP COLUMN IF EXISTS description,
    DROP COLUMN IF EXISTS address,
    DROP COLUMN IF EXISTS is_favourite,
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE IF EXISTS route
    DROP COLUMN IF EXISTS distance_km,
    DROP COLUMN IF EXISTS duration_minutes,
    DROP COLUMN IF EXISTS notes,
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE IF EXISTS user_profile
    DROP COLUMN IF EXISTS bio,
    DROP COLUMN IF EXISTS avatar_url,
    DROP COLUMN IF EXISTS default_latitude,
    DROP COLUMN IF EXISTS default_longitude,
    DROP COLUMN IF EXISTS default_zoom,
    DROP COLUMN IF EXISTS show_temperature,
    DROP COLUMN IF EXISTS show_rain,
    DROP COLUMN IF EXISTS show_wind;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("weather", "0002_new_models_and_fields"),
    ]

    operations = [
        migrations.RunSQL(DROP_UNUSED_TABLES_SQL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(DROP_UNUSED_COLUMNS_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
