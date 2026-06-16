#!/usr/bin/env python3
"""Fetch data from a REST API and store in a local JSON file.

Currenty configured to fetch from the airplanes.live API.
The output file can then be ingested into the `ac` table using `ingest_adsb.py`.

Data is fetched for locations defined in the `locations` table, but only for users
who have opted to receive push notifications (indicating they are active users of the system).

Example:
  python3 scripts/api_fetcher.py

"""
import argparse
from email import parser
import json
import os
import sys
import time
import requests
import subprocess
from typing import Iterable, Dict, Any

# Ensure project root is on sys.path so local modules like `db` can be imported
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import get_conn

FILE_OUTPUT_DIR = "/var/tmp/foxalert/api_fetcher"

def radius_nm():
    # For simplicity, using a fixed radius. In a real implementation, this could be configurable.
    return 5


def get_coords_from_db() -> Iterable[tuple]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ST_Y(geom) AS lat, ST_X(geom) AS lon
                FROM locations
                WHERE username IN (
                    SELECT username FROM push_subscriptions WHERE endpoint IS NOT NULL
                );
                """
            )
            return cur.fetchall()


def fetch_airplanes_live_data(coords: Iterable[tuple], radius: int) -> None:
    # Implementation for fetching data from airplanes.live API
    def url_for_location(lat, lon):
        return f"https://api.airplanes.live/v2/point/{lat}/{lon}/{radius}"
    
    for lat, lon in coords:
        time.sleep(2)  # Be polite and respect API rate limits
        url = url_for_location(lat, lon)
        print(f"Fetching data for location ({lat}, {lon}) from {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Write data to a local JSON file for later ingestion
            filename = f"{FILE_OUTPUT_DIR}/airplanes_live_{lat}_{lon}_{int(time.time())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            # Linux can fork, use it
            subprocess.Popen(['python3', 'scripts/ingest_adsb.py', filename])
        except Exception as e:
            print(f"Error fetching data for location ({lat}, {lon}): {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch data from a REST API and store in a local JSON file. Currently configured to fetch from the airplanes.live API.")
    args = parser.parse_args()

    try:
        Path(FILE_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        coords = get_coords_from_db()
        print(f"Fetched {len(coords)} coordinates from DB for API queries.")
        fetch_airplanes_live_data(coords, radius_nm())
    except Exception as e:
        print('Error during invocation:', e, file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
