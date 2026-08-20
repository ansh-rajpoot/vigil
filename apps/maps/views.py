from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from common.utils import api_response, haversine_distance
from .models import SafetyPOI, SafeRoute
from .serializers import SafetyPOISerializer, SafeRouteSerializer
from .routing_engine import calculate_safe_route_waypoints
from geofencing.models import GeoZone
from geofencing.serializers import GeoZoneSerializer
from risk.models import Blackspot
from risk.serializers import BlackspotSerializer
from emergency.models import SOSAlert, ResponderUnit
from incidents.models import Incident
from alerts.models import EmergencyBroadcast
from alerts.serializers import EmergencyBroadcastSerializer
from tourists.models import TouristProfile
from django.utils import timezone


def gis_explorer_view(request):
    """
    Primary Interactive GIS Map Explorer for Tourists.
    Supports multi-city search (Mumbai, Delhi, Noida, Jaipur, Agra, Goa),
    live layer toggles (tourist places, PCR vans, incidents, restricted zones, police, hospitals),
    and responsive Leaflet GIS visualization.
    """
    pois = SafetyPOI.objects.all()
    blackspots = Blackspot.objects.filter(is_active=True)
    zones = GeoZone.objects.filter(is_active=True)
    cities = get_cities_catalog()
    places = get_all_places_catalog()

    profile = None
    tourist_lat = request.GET.get('lat')
    tourist_lng = request.GET.get('lng')

    if request.user.is_authenticated:
        profile = getattr(request.user, 'tourist_profile', None)
        if profile and profile.current_latitude and profile.current_longitude and not tourist_lat:
            tourist_lat = float(profile.current_latitude)
            tourist_lng = float(profile.current_longitude)

    return render(request, 'maps/gis_explorer.html', {
        'pois': pois,
        'blackspots': blackspots,
        'zones': zones,
        'cities': cities,
        'places': places,
        'profile': profile,
        'tourist_lat': tourist_lat,
        'tourist_lng': tourist_lng,
    })


from .places_catalog import (
    get_all_places_catalog,
    get_cities_catalog,
    search_places,
    get_place_by_id_or_name,
    resolve_place_to_coords,
    reverse_geocode_landmark,
    CITIES_METADATA
)


@login_required
def safe_routes_view(request):
    """Tourist Safe Navigation UI with Leaflet interactive GIS routing."""
    pois = SafetyPOI.objects.all()
    saved_routes = SafeRoute.objects.all()
    blackspots = Blackspot.objects.filter(is_active=True)
    zones = GeoZone.objects.filter(is_active=True)
    all_places = get_all_places_catalog()

    profile = getattr(request.user, 'tourist_profile', None)

    return render(request, 'tourist/safe_routes.html', {
        'pois': pois,
        'saved_routes': saved_routes,
        'blackspots': blackspots,
        'zones': zones,
        'places': all_places,
        'profile': profile,
    })


def place_safety_explorer_view(request):
    """
    Tourist Multi-City Safety Explorer Portal.
    Allows searching tourist places across Mumbai, Delhi, Noida, Jaipur, Agra, and Goa,
    viewing safety index scorecards, live PCR patrol coverage, active incidents, and restricted zones.
    """
    cities = get_cities_catalog()
    all_places = get_all_places_catalog()
    zones = GeoZone.objects.filter(is_active=True)
    blackspots = Blackspot.objects.filter(is_active=True)
    pois = SafetyPOI.objects.all()

    profile = None
    if request.user.is_authenticated:
        profile = getattr(request.user, 'tourist_profile', None)

    return render(request, 'tourist/place_safety_explorer.html', {
        'cities': cities,
        'places': all_places,
        'zones': zones,
        'blackspots': blackspots,
        'pois': pois,
        'profile': profile,
    })


# ==============================================================================
# Geographic REST APIs
# ==============================================================================

class GISLayersAPIView(APIView):
    """
    Aggregated Geographic Layers Endpoint.
    Returns categorized GIS features: tourists, incidents, SOS events,
    hospitals, police stations, lifeguard watchtowers, blackspots, geofences, and fleet responders.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. Safety POIs
        hospitals = SafetyPOI.objects.filter(poi_type='HOSPITAL')
        police_stations = SafetyPOI.objects.filter(poi_type__in=['POLICE', 'TOURIST_POLICE'])
        beach_towers = SafetyPOI.objects.filter(poi_type__in=['BEACH_TOWER', 'TOURIST_KIOSK', 'SAFE_SHELTER'])

        # 2. Blackspots & Hazards
        blackspots = Blackspot.objects.filter(is_active=True)

        # 3. GeoZones (Polygons)
        zones = GeoZone.objects.filter(is_active=True)

        # 4. Open Incidents
        incidents = Incident.objects.exclude(status__in=['RESOLVED', 'FALSE_ALARM'])

        # 5. Active SOS Panic Beacons
        sos_alerts = SOSAlert.objects.filter(status__in=['ACTIVE', 'ACKNOWLEDGED', 'DISPATCHED', 'RESPONDING', 'ON_SCENE'])

        # 6. Active Responders (Fleet)
        responders = ResponderUnit.objects.all()

        # 7. Active Tourists (if authenticated)
        tourists_data = []
        if request.user.is_authenticated:
            active_profiles = TouristProfile.objects.filter(
                trip_status__in=['ACTIVE', 'SOS_ACTIVE'],
                current_latitude__isnull=False,
                current_longitude__isnull=False
            )
            tourists_data = [
                {
                    'id': p.id,
                    'name': p.user.get_full_name() or p.user.username,
                    'latitude': p.current_latitude,
                    'longitude': p.current_longitude,
                    'battery_level': p.battery_level,
                    'trip_status': p.trip_status,
                    'nationality': p.nationality,
                    'last_seen': p.last_location_time.strftime("%H:%M") if p.last_location_time else "Now"
                }
                for p in active_profiles
            ]

        # 8. Active Emergency Alerts
        now = timezone.now()
        active_broadcasts = EmergencyBroadcast.objects.filter(is_active=True, starts_at__lte=now, expires_at__gte=now)

        payload = {
            'hospitals': SafetyPOISerializer(hospitals, many=True).data,
            'police_stations': SafetyPOISerializer(police_stations, many=True).data,
            'beach_towers': SafetyPOISerializer(beach_towers, many=True).data,
            'blackspots': BlackspotSerializer(blackspots, many=True).data,
            'geozones': GeoZoneSerializer(zones, many=True).data,
            'active_alerts': EmergencyBroadcastSerializer(active_broadcasts, many=True).data,
            'incidents': [
                {
                    'id': inc.id,
                    'incident_id': inc.incident_id,
                    'title': inc.title,
                    'category': inc.get_category_display(),
                    'severity': inc.severity,
                    'status': inc.get_status_display(),
                    'latitude': inc.latitude,
                    'longitude': inc.longitude,
                    'location_name': inc.location_name,
                    'created_at': inc.created_at.strftime("%b %d, %H:%M")
                }
                for inc in incidents
            ],
            'sos_events': [
                {
                    'id': s.id,
                    'sos_code': s.sos_id,
                    'tourist_name': s.tourist.user.get_full_name() or s.tourist.user.username,
                    'status': s.status,
                    'status_display': s.get_status_display(),
                    'latitude': s.latitude,
                    'longitude': s.longitude,
                    'triggered_at': s.triggered_at.strftime("%H:%M:%S")
                }
                for s in sos_alerts
            ],
            'responders': [
                {
                    'id': r.id,
                    'unit_code': r.unit_code,
                    'callsign': r.callsign,
                    'agency': r.get_agency_display(),
                    'officer_in_charge': r.officer_in_charge,
                    'contact_number': r.contact_number,
                    'status': r.status,
                    'status_display': r.get_status_display(),
                    'latitude': r.current_latitude,
                    'longitude': r.current_longitude
                }
                for r in responders
            ],
            'tourists': tourists_data,
            'places': get_all_places_catalog(),
            'cities': get_cities_catalog()
        }

        return api_response(success=True, message="GIS layers loaded", data=payload)


class NearbySafeguardsAPIView(APIView):
    """
    Spatial Proximity Query Endpoint.
    Given latitude and longitude, finds nearest police station, hospital, safe haven,
    and identifies any active blackspots or hazard perimeters within radius.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius_km = float(request.query_params.get('radius_km', 5.0))

        if not lat or not lng:
            return api_response(success=False, message="Coordinates 'lat' and 'lng' required", http_code=status.HTTP_400_BAD_REQUEST)

        try:
            curr_lat = float(lat)
            curr_lng = float(lng)
        except ValueError:
            return api_response(success=False, message="Invalid coordinate format", http_code=status.HTTP_400_BAD_REQUEST)

        pois = SafetyPOI.objects.all()
        poi_distances = []
        for p in pois:
            dist = haversine_distance(curr_lat, curr_lng, p.latitude, p.longitude)
            if dist <= radius_km:
                poi_distances.append({
                    'id': p.id,
                    'name': p.name,
                    'type': p.poi_type,
                    'type_display': p.get_poi_type_display(),
                    'latitude': p.latitude,
                    'longitude': p.longitude,
                    'contact_number': p.contact_number,
                    'is_24_hours': p.is_24_hours,
                    'address': p.address,
                    'distance_km': round(dist, 2)
                })

        poi_distances.sort(key=lambda x: x['distance_km'])

        # Categorize nearest
        nearest_police = next((x for x in poi_distances if x['type'] in ['POLICE', 'TOURIST_POLICE']), None)
        nearest_hospital = next((x for x in poi_distances if x['type'] == 'HOSPITAL'), None)
        nearest_shelter = next((x for x in poi_distances if x['type'] in ['SAFE_SHELTER', 'TOURIST_KIOSK', 'BEACH_TOWER']), None)

        # Check nearby blackspots
        blackspots = Blackspot.objects.filter(is_active=True)
        nearby_blackspots = []
        for b in blackspots:
            dist = haversine_distance(curr_lat, curr_lng, b.latitude, b.longitude)
            radius_km_b = (b.radius_meters + 100) / 1000.0
            if dist <= radius_km_b + 1.0:
                nearby_blackspots.append({
                    'id': b.id,
                    'name': b.name,
                    'category': b.get_category_display(),
                    'distance_km': round(dist, 2),
                    'is_inside_hazard': dist <= (b.radius_meters / 1000.0),
                    'safety_advice': b.safety_advice
                })

        nearby_blackspots.sort(key=lambda x: x['distance_km'])

        return api_response(success=True, data={
            'query_location': {'latitude': curr_lat, 'longitude': curr_lng},
            'radius_km': radius_km,
            'nearest_police': nearest_police,
            'nearest_hospital': nearest_hospital,
            'nearest_shelter': nearest_shelter,
            'all_nearby_safeguards': poi_distances[:10],
            'nearby_hazards': nearby_blackspots
        })


class CitiesListAPIView(APIView):
    """
    Returns list of all supported cities with overall safety indices and emergency helplines.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return api_response(success=True, message="Cities catalog retrieved", data=get_cities_catalog())


class PlaceSearchAPIView(APIView):
    """
    Autocomplete & Search endpoint for multi-city landmarks, beaches, transit hubs, and safety POIs.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        city = request.query_params.get('city')
        results = search_places(query=query, city=city)
        return api_response(success=True, message="Places retrieved", data=results)


class PlaceSafetyScorecardAPIView(APIView):
    """
    Consolidated Safety Intelligence Scorecard for a tourist place or coordinates.
    Returns:
    - Overall Safety Score, Security Rating & Illumination Level
    - Active PCR Patrol Vans stationed or en route in the area
    - Active Incidents and Hazard Advisories in radius
    - Restricted / High-Risk Geofence Perimeters
    - Nearby Emergency Hospitals & Police Booths
    - Actionable Tourist Safety Guidance & 24x7 Helplines
    """
    permission_classes = [AllowAny]

    def get(self, request):
        place_ident = request.query_params.get('place')
        city_code = request.query_params.get('city')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')

        place_data = None
        target_lat, target_lng = None, None

        if place_ident:
            place_data = get_place_by_id_or_name(place_ident)
            if place_data:
                target_lat = place_data['latitude']
                target_lng = place_data['longitude']

        if target_lat is None or target_lng is None:
            if lat and lng:
                try:
                    target_lat = float(lat)
                    target_lng = float(lng)
                except ValueError:
                    pass

        if target_lat is None or target_lng is None:
            # Default to city center or Gateway
            if city_code and city_code.upper() in CITIES_METADATA:
                meta = CITIES_METADATA[city_code.upper()]
                target_lat = meta['center_lat']
                target_lng = meta['center_lng']
            else:
                target_lat = 18.9220
                target_lng = 72.8347

        # 1. Base Place Data or fallback
        if not place_data:
            reverse_name = reverse_geocode_landmark(target_lat, target_lng)
            place_data = {
                'id': 'DYNAMIC_LOC',
                'name': reverse_name,
                'city_code': city_code or 'GOA',
                'city_name': (CITIES_METADATA.get(city_code.upper(), {})).get('name', 'Goa'),
                'category': 'LANDMARK',
                'category_display': '📍 Monitored Location',
                'latitude': target_lat,
                'longitude': target_lng,
                'address': f"Coordinates: {target_lat:.4f}°, {target_lng:.4f}°",
                'safety_score': 90,
                'safety_level': 'SAFE',
                'lighting': 'Monitored Sector',
                'crowd_level': 'Moderate Flow',
                'police_coverage': 'Patrol Coverage Available',
                'emergency_phone': '112',
                'pcr_vans': [],
                'active_incidents': [],
                'restricted_zones': [],
                'nearby_hospitals': [],
                'safety_tips': 'Verified safety sector.'
            }

        # 2. Query Live Database Responders in Radius (5km)
        db_responders = ResponderUnit.objects.all()
        nearby_responders = []
        for r in db_responders:
            dist = haversine_distance(target_lat, target_lng, r.current_latitude, r.current_longitude)
            if dist <= 12.0:  # Within 12km
                nearby_responders.append({
                    'id': r.id,
                    'unit_code': r.unit_code,
                    'callsign': r.callsign,
                    'agency': r.get_agency_display(),
                    'officer': r.officer_in_charge,
                    'contact': r.contact_number,
                    'status': r.status,
                    'status_display': r.get_status_display(),
                    'latitude': r.current_latitude,
                    'longitude': r.current_longitude,
                    'distance_km': round(dist, 2),
                    'distance_m': int(dist * 1000)
                })
        nearby_responders.sort(key=lambda x: x['distance_km'])

        # Combine with catalog PCRs if present
        all_pcrs = list(place_data.get('pcr_vans', []))
        for nr in nearby_responders[:4]:
            if not any(x.get('unit_code') == nr['unit_code'] for x in all_pcrs):
                all_pcrs.append(nr)

        # 3. Query Active Incidents in Radius
        db_incidents = Incident.objects.exclude(status__in=['RESOLVED', 'FALSE_ALARM'])
        nearby_incidents = []
        for inc in db_incidents:
            dist = haversine_distance(target_lat, target_lng, inc.latitude, inc.longitude)
            if dist <= 8.0:
                nearby_incidents.append({
                    'id': inc.id,
                    'incident_id': inc.incident_id,
                    'title': inc.title,
                    'category': inc.get_category_display(),
                    'severity': inc.severity,
                    'status': inc.get_status_display(),
                    'latitude': inc.latitude,
                    'longitude': inc.longitude,
                    'distance_km': round(dist, 2),
                    'location_name': inc.location_name
                })
        for cat_inc in place_data.get('active_incidents', []):
            nearby_incidents.append(cat_inc)

        # 4. Query Restricted Zones & Blackspots in Radius
        db_zones = GeoZone.objects.filter(is_active=True)
        nearby_zones = []
        for z in db_zones:
            dist = haversine_distance(target_lat, target_lng, z.center_latitude, z.center_longitude)
            if dist <= 10.0:
                nearby_zones.append({
                    'name': z.name,
                    'code': z.code,
                    'zone_type': z.zone_type,
                    'zone_type_display': z.get_zone_type_display(),
                    'center_latitude': z.center_latitude,
                    'center_longitude': z.center_longitude,
                    'polygon_geojson': z.polygon_geojson,
                    'safety_advisory': z.safety_advisory,
                    'distance_km': round(dist, 2)
                })
        for cat_z in place_data.get('restricted_zones', []):
            if not any(x['name'] == cat_z['name'] for x in nearby_zones):
                nearby_zones.append(cat_z)

        # 5. Query Safety POIs (Police & Hospitals)
        db_pois = SafetyPOI.objects.all()
        nearby_pois = []
        for p in db_pois:
            dist = haversine_distance(target_lat, target_lng, p.latitude, p.longitude)
            if dist <= 10.0:
                nearby_pois.append({
                    'id': p.id,
                    'name': p.name,
                    'type': p.poi_type,
                    'type_display': p.get_poi_type_display(),
                    'latitude': p.latitude,
                    'longitude': p.longitude,
                    'contact_number': p.contact_number,
                    'is_24_hours': p.is_24_hours,
                    'address': p.address,
                    'distance_km': round(dist, 2)
                })
        nearby_pois.sort(key=lambda x: x['distance_km'])

        city_meta = CITIES_METADATA.get(place_data.get('city_code', 'GOA').upper(), CITIES_METADATA['GOA'])

        scorecard = {
            'place': place_data,
            'city_metadata': city_meta,
            'target_coordinates': [target_lat, target_lng],
            'safety_score': place_data.get('safety_score', 90),
            'safety_level': place_data.get('safety_level', 'SAFE'),
            'lighting': place_data.get('lighting', 'Well-Lit Arterial Corridor'),
            'crowd_level': place_data.get('crowd_level', 'Monitored Tourist Flow'),
            'police_coverage': place_data.get('police_coverage', 'High-frequency 24x7'),
            'emergency_phone': place_data.get('emergency_phone', city_meta['police_control_room']),
            'safety_tips': place_data.get('safety_tips', 'Verified monitored tourist destination with active safety checkposts.'),
            'active_pcr_vans': all_pcrs,
            'active_incidents': nearby_incidents,
            'restricted_zones': nearby_zones,
            'nearby_safeguards': nearby_pois[:8],
            'nearby_hospitals': place_data.get('nearby_hospitals', [p for p in nearby_pois if p.get('type') == 'HOSPITAL'])
        }

        return api_response(success=True, message="Safety scorecard compiled successfully", data=scorecard)


class CalculateSafeRouteAPIView(APIView):
    """
    Computes a multi-criteria safety-weighted route between two GPS coordinates or Place Names
    using real OpenStreetMap road networks and PostGIS threat intelligence analysis.
    Avoids active crime/accident blackspots, high-risk geofences, and prioritizes police corridors.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        orig_place = request.data.get('orig_place')
        dest_place = request.data.get('dest_place')
        orig_lat = request.data.get('orig_lat')
        orig_lng = request.data.get('orig_lng')
        dest_lat = request.data.get('dest_lat')
        dest_lng = request.data.get('dest_lng')
        travel_mode = request.data.get('mode', 'walking')

        # 1. Resolve Origin
        o_lat, o_lng, o_name = None, None, None
        if orig_lat is not None and orig_lng is not None and str(orig_lat).strip() and str(orig_lng).strip():
            try:
                o_lat = float(orig_lat)
                o_lng = float(orig_lng)
                o_name = orig_place or reverse_geocode_landmark(o_lat, o_lng)
            except (ValueError, TypeError):
                pass

        if (o_lat is None or o_lng is None) and orig_place:
            resolved_orig = resolve_place_to_coords(orig_place)
            if resolved_orig:
                o_lat, o_lng, o_name = resolved_orig

        # 2. Resolve Destination
        d_lat, d_lng, d_name = None, None, None
        if dest_lat is not None and dest_lng is not None and str(dest_lat).strip() and str(dest_lng).strip():
            try:
                d_lat = float(dest_lat)
                d_lng = float(dest_lng)
                d_name = dest_place or reverse_geocode_landmark(d_lat, d_lng)
            except (ValueError, TypeError):
                pass

        if (d_lat is None or d_lng is None) and dest_place:
            resolved_dest = resolve_place_to_coords(dest_place)
            if resolved_dest:
                d_lat, d_lng, d_name = resolved_dest

        # Validation
        if o_lat is None or o_lng is None:
            return api_response(
                success=False,
                message=f"Starting location not recognized. Please choose a place or provide coordinates.",
                http_code=status.HTTP_400_BAD_REQUEST
            )

        if d_lat is None or d_lng is None:
            return api_response(
                success=False,
                message=f"Destination place not recognized. Please choose a place or provide coordinates.",
                http_code=status.HTTP_400_BAD_REQUEST
            )

        if not (-90.0 <= o_lat <= 90.0) or not (-180.0 <= o_lng <= 180.0) or not (-90.0 <= d_lat <= 90.0) or not (-180.0 <= d_lng <= 180.0):
            return api_response(
                success=False,
                message="Coordinates out of valid geographical bounds (-90 to 90, -180 to 180)",
                http_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            from .routing_service import SafeRoutingEngine
            result = SafeRoutingEngine.compute_safe_corridor(o_lat, o_lng, d_lat, d_lng, mode=travel_mode)
            rec = result['recommended_route']

            # Generate intuitive turn-by-turn guidance notes
            directions = [
                f"1. Start at {o_name or 'Origin'} and proceed along the primary illuminated arterial road.",
                f"2. Follow standard monitored corridor ({rec.get('lighting', 'WELL_LIT').replace('_', ' ').title()}, {rec.get('patrol_coverage', 'Active Patrol')}).",
            ]
            if rec.get('nearby_police'):
                p_first = rec['nearby_police'][0]
                directions.append(f"3. Pass within {p_first['distance_m']}m of {p_first['name']} (24x7 Safety Coverage).")
            if rec.get('nearby_hospitals'):
                h_first = rec['nearby_hospitals'][0]
                directions.append(f"4. Proximity to {h_first['name']} ({h_first['distance_m']}m).")
            directions.append(f"5. Arrive safely at {d_name or 'Destination'}.")

            payload = {
                'origin_name': o_name or f"{o_lat:.4f}, {o_lng:.4f}",
                'destination_name': d_name or f"{d_lat:.4f}, {d_lng:.4f}",
                'origin_coords': [o_lat, o_lng],
                'destination_coords': [d_lat, d_lng],
                'waypoints': rec['waypoints'],
                'distance_km': rec['distance_km'],
                'estimated_minutes': rec['estimated_minutes'],
                'safety_score': rec['safety_score'],
                'detour_applied': rec['detour_applied'],
                'lighting': rec['lighting'],
                'patrol_coverage': rec['patrol_coverage'],
                'summary': rec['summary'],
                'routing_provider': rec['routing_provider'],
                'hazards_detected': rec['hazards_detected'],
                'nearby_police': rec['nearby_police'],
                'nearby_hospitals': rec['nearby_hospitals'],
                'directions': directions,
                'recommended_route': rec,
                'alternative_routes': result['alternative_routes'],
                'evaluation_metadata': result['evaluation_metadata']
            }

            return api_response(success=True, message="Safe route calculated successfully", data=payload)
        except Exception as e:
            return api_response(success=False, message=f"Route calculation error: {str(e)}", http_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SafetyPOIListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        poi_type = request.query_params.get('type')
        queryset = SafetyPOI.objects.all()
        if poi_type:
            queryset = queryset.filter(poi_type=poi_type)
        return api_response(success=True, data=SafetyPOISerializer(queryset, many=True).data)


class SavedSafeRoutesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        routes = SafeRoute.objects.filter(is_verified=True)
        return api_response(success=True, data=SafeRouteSerializer(routes, many=True).data)
