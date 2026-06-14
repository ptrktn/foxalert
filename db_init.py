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
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                );
                """
            )

        conn.commit()

    print("Database initialized successfully.")


if __name__ == "__main__":
    initialize_database()
