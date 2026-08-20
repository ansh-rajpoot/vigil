"""
Compatibility proxy for calculate_safe_route_waypoints.
Delegates directly to SafeRoutingEngine.
"""
from typing import Dict, Any
from .routing_service import SafeRoutingEngine


def calculate_safe_route_waypoints(orig_lat: float, orig_lng: float, dest_lat: float, dest_lng: float) -> Dict[str, Any]:
    """
    Computes a safety-optimized route trajectory between origin and destination.
    Delegates to the decoupled SafeRoutingEngine (real road network + PostGIS threat intelligence).
    """
    res = SafeRoutingEngine.compute_safe_corridor(orig_lat, orig_lng, dest_lat, dest_lng, mode='walking')
    rec = res['recommended_route']
    return {
        'waypoints': rec['waypoints'],
        'distance_km': rec['distance_km'],
        'estimated_minutes': rec['estimated_minutes'],
        'safety_score': rec['safety_score'],
        'detour_applied': rec['detour_applied'],
        'lighting': rec['lighting'],
        'patrol_coverage': rec['patrol_coverage'],
        'safeguards': 'CCTV Monitored Corridor • 2 Emergency Call Boxes • Active Police Checkpost',
        'recommended_route': rec,
        'alternative_routes': res.get('alternative_routes', [])
    }
