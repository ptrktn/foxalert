"""PostgreSQL-backed models for application data.

This module uses psycopg3 to persist users, passkeys, push subscriptions,
and PostGIS location objects.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from db import get_conn


@dataclass
class User:
    username: str
    password: str
    totp_secret: str
    mfa_enabled: bool
    created_at: str


@dataclass
class PushSubscription:
    username: str
    endpoint: str
    p256dh: Optional[str]
    auth: Optional[str]
    created_at: str


@dataclass
class Location:
    username: str
    name: str
    longitude: float
    latitude: float
    created_at: str


def create_user(username: str, password: str, totp_secret: str = "") -> User:
    """Insert a new user into the database."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password, totp_secret) VALUES (%s, %s, %s)"
                " ON CONFLICT (username) DO NOTHING",
                (username, password, totp_secret),
            )
            conn.commit()
            cur.execute(
                "SELECT username, password, totp_secret, mfa_enabled, created_at FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
    return User(*row)


def get_user(username: str) -> Optional[User]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, password, totp_secret, mfa_enabled, created_at FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return User(*row)


def create_passkey(username: str, credential_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO passkeys (username, credential_id) VALUES (%s, %s)"
                " ON CONFLICT (username, credential_id) DO NOTHING",
                (username, credential_id),
            )
            conn.commit()


def get_passkeys(username: str) -> List[str]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT credential_id FROM passkeys WHERE username = %s",
                (username,),
            )
            return [row[0] for row in cur.fetchall()]


def set_mfa_enabled(username: str, enabled: bool = True) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET mfa_enabled = %s WHERE username = %s",
                (enabled, username),
            )
            conn.commit()


def store_push_subscription(username: str, subscription: Dict[str, Any]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO push_subscriptions (username, endpoint, p256dh, auth) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (username, endpoint) DO UPDATE SET p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth",
                (
                    username,
                    subscription.get('endpoint'),
                    subscription.get('keys', {}).get('p256dh'),
                    subscription.get('keys', {}).get('auth'),
                ),
            )
            conn.commit()


def get_push_subscription(username: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return None
            endpoint, p256dh, auth = row
            return {
                'endpoint': endpoint,
                'keys': {
                    'p256dh': p256dh,
                    'auth': auth,
                },
            }


def create_location(username: str, name: str, longitude: float, latitude: float) -> Location:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO locations (username, name, geom) "
                "VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) RETURNING created_at",
                (username, name, longitude, latitude),
            )
            created_at = cur.fetchone()[0]
            conn.commit()
    return Location(username=username, name=name, longitude=longitude, latitude=latitude, created_at=str(created_at))


def find_nearby_locations(username: str, longitude: float, latitude: float, radius_meters: float) -> List[Location]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, ST_X(geom), ST_Y(geom), created_at "
                "FROM locations "
                "WHERE username = %s "
                "AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)",
                (username, longitude, latitude, radius_meters),
            )
            rows = cur.fetchall()
            return [Location(username=username, name=row[0], longitude=row[1], latitude=row[2], created_at=str(row[3])) for row in rows]
