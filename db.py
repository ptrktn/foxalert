"""PostgreSQL connection helper for the FoxAlert application."""

import os

from psycopg import connect

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/foxalert"
)


def get_conn():
    return connect(DATABASE_URL)
