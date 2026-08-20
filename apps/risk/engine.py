from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from django.utils import timezone
from common.utils import haversine_distance
from .models import Blackspot, TouristRiskAssessment
from geofencing.models import GeoZone
from maps.models import SafetyPOI
from alerts.models import EmergencyBroadcast
from incidents.models import Incident


class BaseRiskScoringEngine(ABC):
    """
    Abstract interface for Tourist Risk Scoring Engines.
    Provides a standardized contract so that future PyTorch / Machine Learning
    models can seamlessly replace or augment the heuristic scoring engine.
    """

    @abstractmethod
    def calculate_risk(self, tourist_profile, current_lat: Optional[float] = None, current_lng: Optional[float] = None) -> TouristRiskAssessment:
        """
        Computes a composite risk score (0 - 100) and returns a persisted TouristRiskAssessment.
        """
        pass

    @abstractmethod
    def get_factor_breakdown(self, tourist_profile, current_lat: Optional[float] = None, current_lng: Optional[float] = None) -> Dict[str, Any]:
        """
        Returns an explainable breakdown of the individual weighted risk factors.
        """
        pass


class WeightedHeuristicRiskEngine(BaseRiskScoringEngine):
    """
    Transparent, Deterministic Weighted Heuristic Risk Engine.
    Evaluates objective multi-factor risk across 5 primary dimensions:
      1. Spatial Hazard & Blackspot Proximity (0 - 35 pts)
      2. Temporal Night Vulnerability Curve (0 - 25 pts)
      3. Physical Isolation from Police & Hospitals (0 - 20 pts)
      4. Active Regional Disaster Alerts & Geofences (0 - 15 pts)
      5. Device Battery Telemetry (0 - 10 pts)

    Categories:
      - 0 to 30:  Safe (Minimal / Normal tourist activity)
      - 31 to 60: Moderate (Heightened vigilance advised)
      - 61 to 80: High (Active hazard or curfew in vicinity)
      - 81 to 100: Critical (Immediate danger / incident alert)
    """

    def calculate_risk(self, tourist_profile, current_lat: Optional[float] = None, current_lng: Optional[float] = None) -> TouristRiskAssessment:
        breakdown = self.get_factor_breakdown(tourist_profile, current_lat, current_lng)

        assessment = TouristRiskAssessment.objects.create(
            tourist=tourist_profile,
            overall_score=breakdown['overall_score'],
            risk_level=breakdown['risk_level'],
            spatial_risk_score=breakdown['spatial_score'],
            temporal_risk_score=breakdown['temporal_score'],
            isolation_risk_score=breakdown['isolation_score'],
            crowd_risk_score=breakdown['alert_score'],
            device_health_score=breakdown['device_score'],
            primary_risk_factor=breakdown['primary_factor'],
            ai_recommendation=breakdown['recommendation']
        )
        return assessment

    def get_factor_breakdown(self, tourist_profile, current_lat: Optional[float] = None, current_lng: Optional[float] = None) -> Dict[str, Any]:
        lat = current_lat if current_lat is not None else tourist_profile.current_latitude
        lng = current_lng if current_lng is not None else tourist_profile.current_longitude

        if lat is None or lng is None:
            lat = 15.4989
            lng = 73.8278

        now = timezone.localtime()
        hour = now.hour

        # ----------------------------------------------------------------------
        # 1. Spatial Hazard & Blackspot Proximity (0 - 35 points)
        # ----------------------------------------------------------------------
        spatial_score = 4
        primary_factor = "Designated Tourist Corridor"

        blackspots = Blackspot.objects.filter(is_active=True)
        nearest_blackspot = None
        min_b_dist = float('inf')

        for b in blackspots:
            dist_km = haversine_distance(lat, lng, b.latitude, b.longitude)
            if dist_km < min_b_dist:
                min_b_dist = dist_km
                nearest_blackspot = b

        if nearest_blackspot:
            radius_km = nearest_blackspot.radius_meters / 1000.0
            if min_b_dist <= radius_km:
                spatial_score = min(35, int(nearest_blackspot.risk_weight * 0.35))
                primary_factor = f"Inside {nearest_blackspot.name} ({nearest_blackspot.get_category_display()})"
            elif min_b_dist <= radius_km * 2.0:
                spatial_score = min(22, int(nearest_blackspot.risk_weight * 0.22))
                primary_factor = f"Near {nearest_blackspot.name} ({int(min_b_dist * 1000)}m away)"

        # Check Active GeoZone Containment
        zones = GeoZone.objects.filter(is_active=True)
        for z in zones:
            if z.contains_point(lat, lng):
                if z.zone_type == 'RESTRICTED':
                    spatial_score = max(spatial_score, 35)
                    primary_factor = f"Restricted Boundary Breach: {z.name}"
                elif z.zone_type == 'HIGH_RISK':
                    spatial_score = max(spatial_score, 28)
                    primary_factor = f"High-Risk Hazard Zone: {z.name}"
                elif z.zone_type == 'CURFEW' and z.is_curfew_active_now():
                    spatial_score = max(spatial_score, 30)
                    primary_factor = f"Active Curfew Zone: {z.name}"

        # ----------------------------------------------------------------------
        # 2. Temporal Vulnerability Curve (0 - 25 points)
        # ----------------------------------------------------------------------
        if 0 <= hour < 5:
            temporal_score = 22
            time_label = "Late Night Hours (23:00 - 05:00)"
        elif 22 <= hour < 24:
            temporal_score = 16
            time_label = "Night Hours (22:00 - 24:00)"
        elif 20 <= hour < 22:
            temporal_score = 10
            time_label = "Evening Hours (20:00 - 22:00)"
        elif 5 <= hour < 7:
            temporal_score = 8
            time_label = "Early Dawn (05:00 - 07:00)"
        else:
            temporal_score = 4
            time_label = "Daylight Hours (07:00 - 20:00)"

        # ----------------------------------------------------------------------
        # 3. Physical Isolation from Police & Hospitals (0 - 20 points)
        # ----------------------------------------------------------------------
        pois = SafetyPOI.objects.all()
        min_poi_dist = float('inf')
        for poi in pois:
            dist_km = haversine_distance(lat, lng, poi.latitude, poi.longitude)
            if dist_km < min_poi_dist:
                min_poi_dist = dist_km

        if min_poi_dist > 5.0:
            isolation_score = 20
            isolation_label = "High Isolation (>5 km from emergency services)"
        elif min_poi_dist > 2.5:
            isolation_score = 14
            isolation_label = f"Moderate Distance ({round(min_poi_dist, 1)} km from nearest police/hospital)"
        elif min_poi_dist > 1.0:
            isolation_score = 8
            isolation_label = f"Standard Coverage ({round(min_poi_dist, 1)} km to emergency post)"
        else:
            isolation_score = 2
            isolation_label = "Immediate Help Available (<1 km to active police/medical kiosk)"

        # ----------------------------------------------------------------------
        # 4. Active Regional Disaster Alerts & Incidents (0 - 15 points)
        # ----------------------------------------------------------------------
        alert_score = 2
        active_broadcasts = EmergencyBroadcast.objects.filter(is_active=True)
        if active_broadcasts.filter(severity='CRITICAL').exists():
            alert_score = 15
            primary_factor = "Critical Regional Disaster Broadcast Active"
        elif active_broadcasts.filter(severity='WARNING').exists():
            alert_score = 10
            if "Corridor" in primary_factor:
                primary_factor = "Regional Weather / Hazard Advisory Active"

        # ----------------------------------------------------------------------
        # 5. Device Battery Telemetry (0 - 10 points)
        # ----------------------------------------------------------------------
        battery = tourist_profile.battery_level
        if battery <= 10:
            device_score = 10
            battery_label = f"Critical Battery Depletion ({battery}%)"
        elif battery <= 20:
            device_score = 7
            battery_label = f"Low Battery ({battery}%)"
        elif battery <= 40:
            device_score = 3
            battery_label = f"Moderate Battery ({battery}%)"
        else:
            device_score = 1
            battery_label = f"Healthy Battery ({battery}%)"

        # ----------------------------------------------------------------------
        # Composite Calculation & Category Classification
        # ----------------------------------------------------------------------
        composite_score = min(100, spatial_score + temporal_score + isolation_score + alert_score + device_score)

        if composite_score <= 30:
            risk_level = 'SAFE'
            recommendation = "You are currently in a secure, well-lit tourist area with active police kiosks nearby."
        elif composite_score <= 60:
            risk_level = 'MODERATE'
            recommendation = "Exercise standard caution. Keep emergency contacts accessible and stay along illuminated corridors."
        elif composite_score <= 80:
            risk_level = 'HIGH'
            recommendation = "High risk detected due to terrain, curfew, or isolated surroundings. Re-route towards the nearest safe haven."
        else:
            risk_level = 'CRITICAL'
            recommendation = "IMMINENT SAFETY THREAT. Move immediately to a designated safe haven or tap SOS for responder dispatch."

        return {
            'overall_score': composite_score,
            'risk_level': risk_level,
            'spatial_score': spatial_score,
            'temporal_score': temporal_score,
            'isolation_score': isolation_score,
            'alert_score': alert_score,
            'device_score': device_score,
            'primary_factor': primary_factor,
            'time_label': time_label,
            'isolation_label': isolation_label,
            'battery_label': battery_label,
            'recommendation': recommendation
        }


# ==============================================================================
# Engine Factory
# ==============================================================================

_default_risk_engine = WeightedHeuristicRiskEngine()

def get_risk_engine() -> BaseRiskScoringEngine:
    """
    Returns the active risk scoring engine instance.
    Enables swapping in a PyTorch / ML inference engine when a trained model is deployed.
    """
    return _default_risk_engine


def calculate_tourist_risk(tourist_profile, current_lat: Optional[float] = None, current_lng: Optional[float] = None) -> TouristRiskAssessment:
    """Convenience functional wrapper for risk calculation."""
    return get_risk_engine().calculate_risk(tourist_profile, current_lat, current_lng)
