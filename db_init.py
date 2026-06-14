"""PostgreSQL/PostGIS database initialization.

This script creates the necessary schema and enables PostGIS.
Set DATABASE_URL to a PostgreSQL connection string before running.
"""

import os

from psycopg import connect

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/foxalert"
)


def initialize_database():
    """Initialize PostgreSQL database schema and PostGIS extension."""
    with connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Enable PostGIS extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

            # Create users table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    totp_secret TEXT,
                    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                );
                """
            )

            # Create passkeys table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS passkeys (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                    credential_id TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    UNIQUE(username, credential_id)
                );
                """
            )

            # Create push subscription table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS push_subscriptions (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                    endpoint TEXT NOT NULL,
                    p256dh TEXT,
                    auth TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    UNIQUE(username, endpoint)
                );
                """
            )

            # Create location table for PostGIS object storage
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS locations (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    geom geometry(Point, 4326) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    UNIQUE(username)
                );
                """
            )

            # Create ac table for aircraft tracking data
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ac (
                    id              BIGSERIAL PRIMARY KEY,

                    -- Ingestion metadata
                    ctime          BIGINT NOT NULL,           -- ingestion timestamp (epoch secs)

                    -- Identification
                    hex             VARCHAR(6) NOT NULL,      -- ICAO hex
                    msg_type        TEXT,
                    flight          TEXT,

                    -- Raw fields
                    r               TEXT,
                    t               TEXT,

                    -- Position
                    lat             DOUBLE PRECISION,
                    lon             DOUBLE PRECISION,
                    geom            geometry(Point, 4326),

                    -- Telemetry
                    alt_baro        INTEGER,
                    gs              DOUBLE PRECISION,         -- ground speed
                    true_heading    DOUBLE PRECISION,

                    -- Transponder
                    squawk          TEXT,
                    emergency       TEXT,

                    -- Timing
                    seen_pos        DOUBLE PRECISION,
                    seen            DOUBLE PRECISION,

                    -- Timestamp
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                );
            """
            )

            cur.execute(
                """
                CREATE OR REPLACE FUNCTION ac_set_geom()
                RETURNS trigger AS $$
                BEGIN
                    IF NEW.lat IS NOT NULL AND NEW.lon IS NOT NULL THEN
                        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326);
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER trg_ac_set_geom
                BEFORE INSERT OR UPDATE ON ac
                FOR EACH ROW EXECUTE FUNCTION ac_set_geom();

                CREATE INDEX IF NOT EXISTS idx_locations_geom ON locations USING GIST (geom);
                CREATE INDEX IF NOT EXISTS idx_ac_geom ON ac USING GIST (geom);
                CREATE INDEX IF NOT EXISTS idx_ac_created_at ON ac(created_at);
                CREATE INDEX IF NOT EXISTS idx_ac_hex ON adsb_messages(hex);
                """
            )

        conn.commit()

    print("Database initialized successfully.")


if __name__ == "__main__":
    initialize_database()
