from typing import Dict, Any, List, Tuple
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import GeoZone, TouristZonePresence, GeofenceBreachLog
from risk.engine import calculate_tourist_risk


def broadcast_geofence_event(event_type: str, payload: dict):
    """Broadcasts geofence events to C2 operations channel and tourist device channel."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "c2_operations_feed",
                {
                    "type": "c2_broadcast_event",
                    "data": {
                        "type": event_type,
                        "timestamp": timezone.now().isoformat(),
                        **payload
                    }
                }
            )
            # Push to specific tourist channel if user_id present
            user_id = payload.get('user_id')
            if user_id:
                async_to_sync(channel_layer.group_send)(
                    f"tourist_alerts_{user_id}",
                    {
                        "type": "tourist_alert_message",
                        "data": {
                            "type": event_type,
                            "timestamp": timezone.now().isoformat(),
                            **payload
                        }
                    }
                )
    except Exception as e:
        print(f"Geofence WebSocket broadcast error: {e}")


def process_tourist_geofence_transitions(tourist, current_lat: float, current_lng: float) -> Dict[str, Any]:
    """
    Evaluates tourist location against all active geofences.
    Handles:
      1. Entry detection into SAFE, CAUTION, HIGH_RISK, RESTRICTED, EMERGENCY zones.
      2. Exit detection when moving out of a zone.
      3. Dynamic risk score recalculation upon transition.
      4. Duplicate alert prevention when remaining inside the same zone.
      5. Authority alert dispatch for high risk/restricted breaches.
    """
    all_active_zones = GeoZone.objects.filter(is_active=True)
    containing_zones = [z for z in all_active_zones if z.contains_point(current_lat, current_lng)]

    containing_zone_ids = set(z.id for z in containing_zones)
    active_presences = TouristZonePresence.objects.filter(tourist=tourist, is_active=True)
    previous_zone_ids = set(active_presences.values_list('zone_id', flat=True))

    newly_entered_zone_ids = containing_zone_ids - previous_zone_ids
    exited_zone_ids = previous_zone_ids - containing_zone_ids
    persisting_zone_ids = containing_zone_ids & previous_zone_ids

    alerts_generated: List[Dict[str, Any]] = []
    authority_alerts: List[Dict[str, Any]] = []

    # 1. Handle Exits
    if exited_zone_ids:
        exited_presences = active_presences.filter(zone_id__in=exited_zone_ids)
        for pres in exited_presences:
            pres.is_active = False
            pres.save(update_fields=['is_active'])

            GeofenceBreachLog.objects.create(
                tourist=tourist,
                zone=pres.zone,
                breach_type='ZONE_EXIT',
                latitude=current_lat,
                longitude=current_lng,
                risk_score_after=tourist.risk_assessments.first().overall_score if tourist.risk_assessments.exists() else 15
            )

    # 2. Handle Continuous Occupancy (Prevent Duplicate Alerts)
    if persisting_zone_ids:
        active_presences.filter(zone_id__in=persisting_zone_ids).update(last_detected_at=timezone.now())

    # 3. Handle Newly Entered Zones
    if newly_entered_zone_ids:
        new_zones = [z for z in containing_zones if z.id in newly_entered_zone_ids]

        # Recalculate Risk Score
        risk_assessment = calculate_tourist_risk(tourist, current_lat, current_lng)

        for zone in new_zones:
            # Map Zone Type to Breach / Event Type
            if zone.zone_type == 'RESTRICTED':
                breach_type = 'ENTER_RESTRICTED'
                msg_level = 'CRITICAL'
                tourist_msg = f"⛔ RESTRICTED AREA ALERT: You entered '{zone.name}'. Entry is strictly prohibited. {zone.safety_advisory}"
                notify_authority = True
            elif zone.zone_type == 'EMERGENCY':
                breach_type = 'ENTER_EMERGENCY'
                msg_level = 'CRITICAL'
                tourist_msg = f"🚨 EMERGENCY DISASTER ZONE: You are in '{zone.name}'. Evacuation protocol active. {zone.safety_advisory}"
                notify_authority = True
            elif zone.zone_type == 'HIGH_RISK':
                breach_type = 'ENTER_DANGER'
                msg_level = 'WARNING'
                tourist_msg = f"⚠️ HIGH RISK ZONE: You entered '{zone.name}'. Exercise vigilance. {zone.safety_advisory}"
                notify_authority = True
            elif zone.zone_type == 'CAUTION':
                breach_type = 'ENTRY_CAUTION'
                msg_level = 'ADVISORY'
                tourist_msg = f"⚡ CAUTION ZONE: You entered '{zone.name}'. {zone.safety_advisory or 'Stay along illuminated corridors.'}"
                notify_authority = False
            else:  # SAFE
                breach_type = 'ENTRY_SAFE'
                msg_level = 'SAFE'
                tourist_msg = f"🛡️ SAFE HAVEN: You entered '{zone.name}'. Active police presence and CCTV monitoring active."
                notify_authority = False

            # Create Active Presence
            TouristZonePresence.objects.create(
                tourist=tourist,
                zone=zone,
                is_active=True,
                alert_dispatched=True,
                authority_notified=notify_authority
            )

            # Create Audit Log
            log = GeofenceBreachLog.objects.create(
                tourist=tourist,
                zone=zone,
                breach_type=breach_type,
                latitude=current_lat,
                longitude=current_lng,
                risk_score_after=risk_assessment.overall_score,
                authority_notified=notify_authority
            )

            alert_info = {
                'zone_id': zone.id,
                'zone_name': zone.name,
                'zone_type': zone.zone_type,
                'level': msg_level,
                'message': tourist_msg,
                'risk_score': risk_assessment.overall_score,
                'authority_notified': notify_authority,
                'user_id': tourist.user.id,
                'tourist_name': tourist.user.get_full_name() or tourist.user.username,
                'latitude': current_lat,
                'longitude': current_lng,
            }
            alerts_generated.append(alert_info)
            if notify_authority:
                authority_alerts.append(alert_info)
                # Live broadcast to C2 desk
                broadcast_geofence_event("high_risk_zone_entry", alert_info)

    return {
        'is_in_any_zone': len(containing_zones) > 0,
        'containing_zones': [
            {
                'id': z.id,
                'name': z.name,
                'zone_type': z.zone_type,
                'color': z.get_color_hex(),
                'safety_advisory': z.safety_advisory
            } for z in containing_zones
        ],
        'new_alerts': alerts_generated,
        'authority_alerts_dispatched': authority_alerts,
        'persisting_zone_count': len(persisting_zone_ids),
        'newly_entered_count': len(newly_entered_zone_ids),
        'exited_count': len(exited_zone_ids),
    }
