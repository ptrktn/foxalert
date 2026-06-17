import math

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

print(time_to_cover_radius())