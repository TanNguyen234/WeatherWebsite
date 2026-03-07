# Generated manually – adds new models and fields introduced in the model refactor.
# Uses SeparateDatabaseAndState because 0001_initial was FAKED on a database that
# already had the original tables.  The "state" side is empty (0001 already tracks
# all new models); the "database" side creates missing tables / columns safely with
# IF NOT EXISTS / DO NOTHING guards.

from django.db import migrations


_CREATE_USER_PROFILE = """
CREATE TABLE IF NOT EXISTS user_profile (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL DEFAULT 'user',
    bio             TEXT        NOT NULL DEFAULT '',
    avatar_url      VARCHAR(500) NOT NULL DEFAULT '',
    default_latitude  DOUBLE PRECISION,
    default_longitude DOUBLE PRECISION,
    default_zoom    SMALLINT    NOT NULL DEFAULT 6,
    show_temperature BOOLEAN    NOT NULL DEFAULT TRUE,
    show_rain        BOOLEAN    NOT NULL DEFAULT TRUE,
    show_wind        BOOLEAN    NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
"""

_CREATE_AREA = """
CREATE TABLE IF NOT EXISTS area (
    id                BIGSERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES auth_user(id)       ON DELETE CASCADE,
    center_location_id INTEGER NOT NULL REFERENCES user_location(id)  ON DELETE CASCADE,
    name              VARCHAR(255) NOT NULL DEFAULT '',
    radius_km         DOUBLE PRECISION NOT NULL,
    notes             TEXT NOT NULL DEFAULT '',
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
"""

_CREATE_INTERACTION_LOG = """
CREATE TABLE IF NOT EXISTS interaction_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    detail      JSONB,
    ip_address  INET,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS interaction_log_action_idx ON interaction_log (action_type);
CREATE INDEX IF NOT EXISTS interaction_log_created_idx ON interaction_log (created_at);
"""

_ADD_USER_LOCATION_COLS = """
ALTER TABLE user_location
    ADD COLUMN IF NOT EXISTS description TEXT        NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS address     VARCHAR(500) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS is_favourite BOOLEAN    NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_user_location_user_fav ON user_location (user_id, is_favourite);
"""

_ADD_LOCATION_GROUP_COLS = """
ALTER TABLE location_group
    ADD COLUMN IF NOT EXISTS description TEXT        NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS color       VARCHAR(7)  NOT NULL DEFAULT '#3b82f6';
"""

_ADD_ROUTE_COLS = """
ALTER TABLE route
    ADD COLUMN IF NOT EXISTS distance_km      DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS duration_minutes DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS notes            TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS updated_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
"""

_DROP_SCHEMA = """
DROP TABLE IF EXISTS interaction_log CASCADE;
DROP TABLE IF EXISTS area CASCADE;
DROP TABLE IF EXISTS user_profile CASCADE;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('weather', '0001_initial'),
    ]

    operations = [
        # SeparateDatabaseAndState: state=[] because 0001 already describes all
        # models; database=RunSQL does the actual DDL that was missing.
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql=_CREATE_USER_PROFILE,
                    reverse_sql="DROP TABLE IF EXISTS user_profile CASCADE;",
                ),
                migrations.RunSQL(
                    sql=_CREATE_AREA,
                    reverse_sql="DROP TABLE IF EXISTS area CASCADE;",
                ),
                migrations.RunSQL(
                    sql=_CREATE_INTERACTION_LOG,
                    reverse_sql="DROP TABLE IF EXISTS interaction_log CASCADE;",
                ),
                migrations.RunSQL(
                    sql=_ADD_USER_LOCATION_COLS,
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql=_ADD_LOCATION_GROUP_COLS,
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql=_ADD_ROUTE_COLS,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
