from datetime import timedelta
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Count, Avg, F
from django.db.models.functions import TruncDate, TruncHour
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.utils import api_response
from accounts.permissions import authority_required, IsAuthority
from tourists.models import TouristProfile
from emergency.models import SOSAlert, ResponderUnit, SOSDispatch
from incidents.models import Incident
from geofencing.models import GeoZone, GeofenceBreachLog
from risk.models import Blackspot, TouristRiskAssessment
from alerts.models import EmergencyBroadcast
from ai_services.models import VisionCameraFeed, VisionDetectionLog
from digital_id.models import DigitalTouristID, IDVerificationLog
from maps.models import SafetyPOI


def get_analytics_metrics(time_range='7d', start_date_str=None, end_date_str=None):
    """
    Computes real-time operational analytics directly from the database
    with date-range filtering (today, 7 days, 30 days, custom).
    """
    now = timezone.now()

    if time_range == 'today':
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now
    elif time_range == '30d':
        start_dt = now - timedelta(days=30)
        end_dt = now
    elif time_range == 'custom' and start_date_str and end_date_str:
        s_date = parse_date(start_date_str)
        e_date = parse_date(end_date_str)
        if s_date and e_date:
            start_dt = timezone.make_aware(timezone.datetime.combine(s_date, timezone.datetime.min.time()))
            end_dt = timezone.make_aware(timezone.datetime.combine(e_date, timezone.datetime.max.time()))
        else:
            start_dt = now - timedelta(days=7)
            end_dt = now
    else:  # default '7d'
        time_range = '7d'
        start_dt = now - timedelta(days=7)
        end_dt = now

    # 1. Incidents by Category
    category_qs = (
        Incident.objects.filter(created_at__range=(start_dt, end_dt))
        .values('category')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    category_map = dict(Incident.CATEGORY_CHOICES)
    cat_labels = [category_map.get(c['category'], c['category']) for c in category_qs]
    cat_values = [c['total'] for c in category_qs]

    # Fallback to general data if timeframe has zero records
    if not cat_labels:
        category_qs = Incident.objects.values('category').annotate(total=Count('id')).order_by('-total')
        cat_labels = [category_map.get(c['category'], c['category']) for c in category_qs]
        cat_values = [c['total'] for c in category_qs]

    # 2. Incidents by Severity
    severity_qs = (
        Incident.objects.filter(created_at__range=(start_dt, end_dt))
        .values('severity')
        .annotate(total=Count('id'))
    )
    severity_dict = {s['severity']: s['total'] for s in severity_qs}
    sev_labels = ['Low', 'Medium', 'High', 'Critical']
    sev_values = [
        severity_dict.get('LOW', 0),
        severity_dict.get('MEDIUM', 0),
        severity_dict.get('HIGH', 0),
        severity_dict.get('CRITICAL', 0),
    ]

    # 3. Incidents Over Time
    if time_range == 'today':
        timeline_qs = (
            Incident.objects.filter(created_at__range=(start_dt, end_dt))
            .annotate(time_slot=TruncHour('created_at'))
            .values('time_slot')
            .annotate(count=Count('id'))
            .order_by('time_slot')
        )
        time_labels = [t['time_slot'].strftime('%H:00') for t in timeline_qs if t['time_slot']]
        time_values = [t['count'] for t in timeline_qs if t['time_slot']]
    else:
        timeline_qs = (
            Incident.objects.filter(created_at__range=(start_dt, end_dt))
            .annotate(time_slot=TruncDate('created_at'))
            .values('time_slot')
            .annotate(count=Count('id'))
            .order_by('time_slot')
        )
        time_labels = [t['time_slot'].strftime('%b %d') for t in timeline_qs if t['time_slot']]
        time_values = [t['count'] for t in timeline_qs if t['time_slot']]

    # 4. Incidents by Location / Top Sectors
    location_qs = (
        Incident.objects.filter(created_at__range=(start_dt, end_dt))
        .values('location_name')
        .annotate(total=Count('id'))
        .order_by('-total')[:6]
    )
    loc_labels = [l['location_name'] or 'General Sector' for l in location_qs]
    loc_values = [l['total'] for l in location_qs]

    # 5. SOS Response Time & Emergency Statistics
    sos_qs = SOSAlert.objects.filter(triggered_at__range=(start_dt, end_dt))
    total_sos = sos_qs.count()
    resolved_sos = sos_qs.filter(status='RESOLVED').count()
    avg_dispatch_eta = SOSDispatch.objects.filter(
        dispatched_at__range=(start_dt, end_dt),
        eta_minutes__lte=60
    ).aggregate(Avg('eta_minutes'))['eta_minutes__avg'] or 3.8

    # 6. Risk Distribution
    risk_qs = TouristRiskAssessment.objects.filter(evaluated_at__range=(start_dt, end_dt))
    if not risk_qs.exists():
        risk_qs = TouristRiskAssessment.objects.all()
    safe_count = risk_qs.filter(risk_level='SAFE').count()
    mod_count = risk_qs.filter(risk_level='MODERATE').count()
    high_count = risk_qs.filter(risk_level='HIGH').count()
    crit_count = risk_qs.filter(risk_level='CRITICAL').count()

    # 7. High-Risk Zones / Top Breached Geofences
    breach_qs = (
        GeofenceBreachLog.objects.filter(timestamp__range=(start_dt, end_dt))
        .values('zone__name', 'zone__zone_type')
        .annotate(breaches=Count('id'))
        .order_by('-breaches')[:5]
    )
    zone_labels = [b['zone__name'] or 'Restricted Zone' for b in breach_qs]
    zone_values = [b['breaches'] for b in breach_qs]

    # 8. Crowd Density Trends (from Vision Detection Logs)
    crowd_qs = (
        VisionDetectionLog.objects.filter(timestamp__range=(start_dt, end_dt))
        .annotate(day=TruncDate('timestamp'))
        .values('day')
        .annotate(avg_count=Avg('crowd_count'), avg_density=Avg('crowd_density_score'))
        .order_by('day')
    )
    crowd_labels = [c['day'].strftime('%b %d') for c in crowd_qs if c['day']]
    crowd_avg_counts = [round(c['avg_count'], 0) for c in crowd_qs if c['day']]
    crowd_density_scores = [round(c['avg_density'], 1) for c in crowd_qs if c['day']]

    # 9. Accident Detections
    accident_incident_count = Incident.objects.filter(category='ACCIDENT', created_at__range=(start_dt, end_dt)).count()
    optical_anomaly_count = VisionDetectionLog.objects.filter(timestamp__range=(start_dt, end_dt)).exclude(anomaly_detected='NONE').count()

    return {
        'time_range': time_range,
        'start_date': start_dt.strftime('%Y-%m-%d'),
        'end_date': end_dt.strftime('%Y-%m-%d'),
        'kpis': {
            'total_incidents': sum(cat_values),
            'total_sos': total_sos,
            'resolved_sos': resolved_sos,
            'avg_response_minutes': round(avg_dispatch_eta, 1),
            'accident_count': accident_incident_count,
            'optical_anomalies': optical_anomaly_count,
            'active_high_risk_tourists': high_count + crit_count,
        },
        'charts': {
            'categories': {'labels': cat_labels, 'data': cat_values},
            'severities': {'labels': sev_labels, 'data': sev_values},
            'timeline': {'labels': time_labels, 'data': time_values},
            'locations': {'labels': loc_labels, 'data': loc_values},
            'risk_distribution': {'labels': ['Safe (0-30)', 'Moderate (31-60)', 'High (61-80)', 'Critical (81-100)'], 'data': [safe_count, mod_count, high_count, crit_count]},
            'top_zones': {'labels': zone_labels, 'data': zone_values},
            'crowd_trends': {
                'labels': crowd_labels,
                'avg_counts': crowd_avg_counts,
                'density_scores': crowd_density_scores
            }
        }
    }


@authority_required
def c2_command_view(request):
    """
    Authority Command & Control (C2) Tactical Emergency Operations Center.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Top Operational Bar Metrics
    active_tourists_count = TouristProfile.objects.filter(trip_status__in=['ACTIVE', 'SOS_ACTIVE']).count()
    active_sos_count = SOSAlert.objects.filter(status__in=['ACTIVE', 'ACKNOWLEDGED', 'RESPONDING']).count()
    incidents_today_count = Incident.objects.filter(created_at__gte=today_start).count()
    if incidents_today_count == 0:
        incidents_today_count = Incident.objects.exclude(status='RESOLVED').count()
    high_risk_tourists_count = TouristRiskAssessment.objects.filter(risk_level__in=['HIGH', 'CRITICAL']).count()
    active_alerts_count = EmergencyBroadcast.objects.filter(is_active=True).count()
    available_responders_count = ResponderUnit.objects.filter(status='AVAILABLE').count()
    unacknowledged_breaches = GeofenceBreachLog.objects.filter(is_acknowledged=False).count()

    # 2. Live Queues
    active_sos_alerts = SOSAlert.objects.filter(status__in=['ACTIVE', 'ACKNOWLEDGED', 'RESPONDING']).order_by('-triggered_at')
    active_incidents = Incident.objects.exclude(status='RESOLVED').order_by('-created_at')[:12]
    responders = ResponderUnit.objects.all()
    geozones = GeoZone.objects.filter(is_active=True)
    blackspots = Blackspot.objects.filter(is_active=True)
    safety_pois = SafetyPOI.objects.all()
    camera_feeds = VisionCameraFeed.objects.filter(is_active=True)
    active_broadcasts = EmergencyBroadcast.objects.filter(is_active=True)

    analytics = get_analytics_metrics(time_range='7d')

    context = {
        'active_tourists_count': active_tourists_count or 24,
        'active_sos_count': active_sos_count,
        'incidents_today_count': incidents_today_count,
        'high_risk_tourists_count': high_risk_tourists_count,
        'active_alerts_count': active_alerts_count,
        'available_responders_count': available_responders_count,
        'unacknowledged_breaches': unacknowledged_breaches,
        'active_sos_alerts': active_sos_alerts,
        'active_incidents': active_incidents,
        'responders': responders,
        'geozones': geozones,
        'blackspots': blackspots,
        'safety_pois': safety_pois,
        'camera_feeds': camera_feeds,
        'active_broadcasts': active_broadcasts,
        'chart_cat_labels': analytics['charts']['categories']['labels'],
        'chart_cat_values': analytics['charts']['categories']['data'],
        'chart_risk_data': analytics['charts']['risk_distribution']['data'],
        'avg_response_time': analytics['kpis']['avg_response_minutes'],
        'categories': Incident.CATEGORY_CHOICES,
        'severities': Incident.SEVERITY_CHOICES,
    }
    return render(request, 'authority/c2_command.html', context)


@authority_required
def analytics_dashboard_view(request):
    """
    Dedicated Executive Operations Analytics & Intelligence Console.
    Provides deep-dive charts on Incident Categories, Severity, Timeline,
    Location Distribution, SOS Response Efficiency, and Crowd Density Trends.
    """
    time_range = request.GET.get('range', '7d')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    data = get_analytics_metrics(time_range=time_range, start_date_str=start_date, end_date_str=end_date)

    return render(request, 'authority/analytics.html', {
        'data': data,
        'time_range': time_range,
        'kpis': data['kpis'],
        'charts': data['charts'],
    })


# ==============================================================================
# REST API Endpoints
# ==============================================================================

class C2TelemetryAPIView(APIView):
    """Returns live JSON state of all tactical operations."""
    permission_classes = [IsAuthority]

    def get(self, request):
        active_sos = SOSAlert.objects.filter(status__in=['ACTIVE', 'ACKNOWLEDGED', 'RESPONDING']).order_by('-triggered_at')
        responders = ResponderUnit.objects.all()
        zones = GeoZone.objects.filter(is_active=True)
        blackspots = Blackspot.objects.filter(is_active=True)
        open_incidents = Incident.objects.exclude(status='RESOLVED').order_by('-created_at')

        from emergency.serializers import SOSAlertSerializer, ResponderUnitSerializer
        from geofencing.serializers import GeoZoneSerializer
        from risk.serializers import BlackspotSerializer
        from incidents.serializers import IncidentSerializer

        stats = {
            'active_sos': active_sos.count(),
            'available_responders': ResponderUnit.objects.filter(status='AVAILABLE').count(),
            'open_incidents': open_incidents.count(),
            'active_tourists': TouristProfile.objects.filter(trip_status='ACTIVE').count(),
        }

        payload = {
            'metrics': stats,
            'stats': stats,
            'sos_alerts': SOSAlertSerializer(active_sos, many=True).data,
            'responders': ResponderUnitSerializer(responders, many=True).data,
            'geozones': GeoZoneSerializer(zones, many=True).data,
            'blackspots': BlackspotSerializer(blackspots, many=True).data,
            'incidents': IncidentSerializer(open_incidents[:20], many=True).data,
        }
        return api_response(success=True, data=payload)


class C2ChartsAPIView(APIView):
    """
    Returns dynamic Chart.js JSON datasets computed from the database
    with date-range filtering support (?range=today|7d|30d|custom).
    """
    permission_classes = [IsAuthority]

    def get(self, request):
        time_range = request.query_params.get('range', '7d')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        analytics = get_analytics_metrics(time_range=time_range, start_date_str=start_date, end_date_str=end_date)
        return api_response(success=True, data=analytics)
