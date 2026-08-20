import math
import hashlib
import hmac
import time
from rest_framework.response import Response
from rest_framework import status

try:
    from shapely.geometry import Point, Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points in kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def point_in_polygon(lat: float, lon: float, polygon_geojson: dict | list) -> bool:
    """
    Checks if a (lat, lon) point lies within a polygon.
    Handles GeoJSON coordinates format: [[[lng, lat], [lng, lat], ...]]
    """
    if not polygon_geojson:
        return False

    coords = []
    if isinstance(polygon_geojson, dict):
        if 'coordinates' in polygon_geojson:
            coords = polygon_geojson['coordinates'][0]
    elif isinstance(polygon_geojson, list):
        if len(polygon_geojson) > 0 and isinstance(polygon_geojson[0], list):
            if isinstance(polygon_geojson[0][0], list):
                coords = polygon_geojson[0]
            else:
                coords = polygon_geojson

    if not coords or len(coords) < 3:
        return False

    if SHAPELY_AVAILABLE:
        try:
            # Note: GeoJSON stores [lng, lat]
            poly = Polygon([(c[0], c[1]) for c in coords])
            pt = Point(lon, lat)
            return poly.contains(pt) or poly.touches(pt)
        except Exception:
            pass

    # Pure Python Ray Casting algorithm fallback
    x = lon
    y = lat
    n = len(coords)
    inside = False

    p1x, p1y = coords[0][0], coords[0][1]
    for i in range(1, n + 1):
        p2x, p2y = coords[i % n][0], coords[i % n][1]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def generate_secure_crypto_hash(data: str) -> str:
    """Generate SHA-256 hash for secure verification records."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def generate_dynamic_totp_token(secret: str, step: int = 30) -> str:
    """
    Generate dynamic time-based 6-digit verification token (TOTP-like).
    Changes every `step` seconds.
    """
    current_step = int(time.time() // step)
    msg = current_step.to_bytes(8, byteorder='big')
    h = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).digest()
    offset = h[-1] & 0x0F
    code = ((h[offset] & 0x7F) << 24 |
            (h[offset + 1] & 0xFF) << 16 |
            (h[offset + 2] & 0xFF) << 8 |
            (h[offset + 3] & 0xFF)) % 1000000
    return f"{code:06d}"


def verify_dynamic_totp_token(secret: str, token: str, step: int = 30, window: int = 1) -> bool:
    """
    Verify dynamic token allowing for clock drift within `window` steps.
    """
    current_step = int(time.time() // step)
    for i in range(-window, window + 1):
        step_val = current_step + i
        msg = step_val.to_bytes(8, byteorder='big')
        h = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).digest()
        offset = h[-1] & 0x0F
        code = ((h[offset] & 0x7F) << 24 |
                (h[offset + 1] & 0xFF) << 16 |
                (h[offset + 2] & 0xFF) << 8 |
                (h[offset + 3] & 0xFF)) % 1000000
        if f"{code:06d}" == str(token).strip():
            return True
    return False


def api_response(success: bool = True, message: str = "", data: any = None, errors: any = None, http_code: int = status.HTTP_200_OK):
    """Standardized JSON API response structure."""
    payload = {
        "success": success,
        "message": message,
        "data": data,
        "errors": errors,
        "timestamp": int(time.time())
    }
    return Response(payload, status=http_code)
