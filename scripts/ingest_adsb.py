#!/usr/bin/env python3
"""Ingest ADS-B aircraft data from JSON files into the `ac` table.

Supports files that are either a JSON object with an `ac` array (like `data.json`),
or a top-level JSON array of records, or newline-delimited JSON (NDJSON).

Example:
  python3 scripts/ingest_adsb.py data.json

"""
import argparse
import json
import os
import sys
import time
from typing import Iterable, Dict, Any

# Ensure project root is on sys.path so local modules like `db` can be imported
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import get_conn

BATCH_SIZE = 200

COLUMNS = [
    'ctime', 'hex', 'msg_type', 'flight', 'r', 't',
    'lat', 'lon', 'alt_baro', 'gs', 'true_heading',
    'squawk', 'emergency', 'seen_pos', 'seen'
]

INSERT_SQL = (
    "INSERT INTO ac (" + ",".join(COLUMNS) + ")\n"
    "VALUES (" + ",".join(["%s"] * len(COLUMNS)) + ")"
)


def load_records(path: str) -> Iterable[Dict[str, Any]]:
    text = open(path, 'r', encoding='utf-8').read()
    # try standard JSON
    try:
        payload = json.loads(text)
    except Exception:
        # fall back to NDJSON
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
        return

    # If payload is dict with 'ac' key (our sample), yield each record and attach top-level ctime
    if isinstance(payload, dict):
        meta_ctime = payload.get('ctime')
        if 'ac' in payload and isinstance(payload['ac'], list):
            for rec in payload['ac']:
                if meta_ctime is not None and 'ctime' not in rec:
                    rec['ctime'] = meta_ctime
                yield rec
            return
        # If dict is a single record, yield it
        yield payload
        return

    # If payload is a list of records
    if isinstance(payload, list):
        for rec in payload:
            yield rec
        return


def record_to_row(rec: Dict[str, Any]) -> tuple:
    # ctime: prefer existing numeric ctime, else epoch seconds
    ctime = rec.get('ctime') or int(time.time())
    # map keys to columns (note: payload uses "type" -> msg_type)
    return (
        ctime,
        rec.get('hex'),
        rec.get('type') or rec.get('msg_type'),
        rec.get('flight'),
        rec.get('r'),
        rec.get('t'),
        rec.get('lat'),
        rec.get('lon'),
        rec.get('alt_baro'),
        rec.get('gs'),
        rec.get('true_heading'),
        rec.get('squawk'),
        rec.get('emergency'),
        rec.get('seen_pos'),
        rec.get('seen')
    )


def ingest(path: str, dry_run: bool = False) -> None:
    rows = []
    count = 0
    for rec in load_records(path):
        rows.append(record_to_row(rec))
        if len(rows) >= BATCH_SIZE:
            if not dry_run:
                write_batch(rows)
            count += len(rows)
            print(f"Inserted {count} rows...", end='\r')
            rows.clear()

    if rows:
        if not dry_run:
            write_batch(rows)
        count += len(rows)

    print(f"\nDone. Inserted {count} rows from {path}.")


def write_batch(rows: Iterable[tuple]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, rows)
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest ADS-B JSON into the ac table")
    parser.add_argument('path', help='Path to JSON file (array, object with `ac`, or NDJSON)')
    parser.add_argument('--dry-run', action='store_true', help='Parse file but do not write to DB')
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print('File not found:', args.path, file=sys.stderr)
        return 2

    try:
        ingest(args.path, dry_run=args.dry_run)
    except Exception as e:
        print('Error during ingestion:', e, file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
