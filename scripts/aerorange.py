import csv
import json
import math
from pathlib import Path
import os
from time import sleep
import uuid

aircraft = {}

def distance_nm(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two lat/lon points in nautical miles.
    Inputs are in decimal degrees.
    """

    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Earth radius in nautical miles
    R_nm = 3440.065

    return R_nm * c


# Example usage:
# lat1, lon1 = 36.6000, 140.6500   # Hitachi City
# lat2, lon2 = 35.6804, 139.7690   # Tokyo Station

# print("Distance (NM):", distance_nm(lat1, lon1, lat2, lon2))

def time_to_cover_radius(gs_knots=460, radius_nm=5):
    """
    Calculate time (in minutes) for an aircraft to cover 2 * radius_nm
    at a given ground speed in knots.

    gs_knots: aircraft ground speed in knots (nm per hour)
    radius_nm: radius in nautical miles
    """
    distance_nm = 2 * radius_nm
    hours = distance_nm / gs_knots
    minutes = hours * 60
    return minutes


def get_aircraft_data(file_path=None, has_header=False, fieldnames=None):
    """Read aircraft data from a CSV file into the global aircraft dict.

    has_header: whether the CSV contains a header row.
    fieldnames: optional list of column names for headerless CSVs.
    """
    if file_path is None:
        # default to ../data/aircraft.csv relative to this script
        file_path = Path(__file__).parent.parent / "data" / "aircraft.csv"
    # allow file_path to be a str or Path
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Aircraft CSV not found: {file_path}")

    with file_path.open(newline="", encoding="utf-8") as csvfile:
        if has_header:
            reader = csv.DictReader(csvfile, delimiter=';')
        else:
            if fieldnames is not None:
                reader = csv.DictReader(csvfile, fieldnames=fieldnames, delimiter=';')
            else:
                reader = csv.reader(csvfile, delimiter=';')

        for row in reader:
            if isinstance(row, dict):
                key = row.get("icao") or row.get("r")
            else:
                key = None
                row = {f"col{idx+1}": value for idx, value in enumerate(row)}

            if not key:
                key = uuid.uuid4().hex  # Generate a unique key if 'icao' or 'r' is missing

            aircraft[key] = row
    return aircraft


def get_military_aircraft():
    """Return a dictionary of military aircraft from the global aircraft dict."""
    return {k: v for k, v in aircraft.items() if v.get("flags", "").startswith("1")}


def monitor_range(aircraft, src = "/run/readsb/aircraft.json"):
    """Monitor aircraft within a certain range from a source file."""
    src_path = Path(src)
    if not src_path.exists():
        print(f"Source file {src_path} does not exist.")
        return

    while True:
        notify = False
        with src_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        ac = [i.get("hex") for i in data.get("aircraft", [])]
        if not ac:
            print("No aircraft data found in the source file.")
            return

        print(f"Found {len(ac)} aircraft in the source file.")

        for icao, info in aircraft.items():
            if icao in ac:
                print(f"Aircraft {icao} is within range.")
                notify = True

        if notify:
            print("Notification: Aircraft detected within range.")
            break  # Exit after the first notification for demonstration purposes

        sleep(120)




if __name__ == "__main__":
    print(time_to_cover_radius())
    data = get_aircraft_data(has_header=False, fieldnames=[
        "icao", "r", "t", "flags", "desc", "c6", "c7", "c8"
    ])
    print(f"Loaded {len(data)} aircraft rows from CSV")
    print("Sample aircraft data:", list(data.items())[:3])
    mil = get_military_aircraft()
    print(f"Found {len(mil)} military aircraft")
    print("Sample military aircraft data:", list(mil.items())[:3])
    monitor_range(mil)