import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from common.utils import api_response, verify_dynamic_totp_token
from .models import DigitalTouristID, IDVerificationLog
from .serializers import DigitalTouristIDSerializer
from tourists.models import TouristProfile


@login_required
def tourist_id_card_view(request):
    """
    Tourist view of their official Digital ID card.
    Displays interactive 3D flip card, live rotating TOTP countdown, and cryptographic QR code.
    """
    profile = get_object_or_404(TouristProfile, user=request.user)
    digital_id, created = DigitalTouristID.objects.get_or_create(
        tourist=profile,
        defaults={
            'id_number': f"VGL-{timezone.now().year}-T89Q2",
            'crypto_hash': 'sha256_mock_hash_seed',
            'valid_until': timezone.now() + timezone.timedelta(days=30),
            'verification_token_secret': 'sih_tourist_secret_key_2026'
        }
    )
    if created or not digital_id.qr_code_image:
        digital_id.generate_qr_code()

    emergency_contacts = request.user.emergency_contacts.all()

    context = {
        'profile': profile,
        'digital_id': digital_id,
        'emergency_contacts': emergency_contacts,
        'qr_payload': digital_id.get_qr_payload_dict(),
    }
    return render(request, 'tourist/digital_id.html', context)


def public_verify_portal_view(request):
    """
    Official Law Enforcement & Checkpoint Verification Portal.
    Allows instant camera scanning, manual ID lookup, or direct verification from QR URL query params.
    """
    prefill_id = request.GET.get('id', '')
    prefill_token = request.GET.get('token', '')
    recent_verifications = IDVerificationLog.objects.all().order_by('-timestamp')[:8]

    return render(request, 'public/verify_id.html', {
        'recent_verifications': recent_verifications,
        'prefill_id': prefill_id,
        'prefill_token': prefill_token
    })


# ==============================================================================
# REST API Endpoints
# ==============================================================================

class DynamicQRTokenAPIView(APIView):
    """Returns freshly rotated dynamic TOTP token & refreshed QR payload."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, 'tourist_profile', None)
        if not profile:
            return api_response(success=False, message="Tourist profile not found", http_code=status.HTTP_404_NOT_FOUND)

        digital_id = get_object_or_404(DigitalTouristID, tourist=profile)
        # Regenerate QR image with current payload
        digital_id.generate_qr_code()

        payload = digital_id.get_qr_payload_dict()
        expires_in = 30 - int(timezone.now().timestamp() % 30)

        return api_response(success=True, message="Dynamic QR refreshed", data={
            'id_number': digital_id.id_number,
            'totp': payload['totp'],
            'payload': payload,
            'qr_image_url': digital_id.qr_code_image.url if digital_id.qr_code_image else None,
            'expires_in_seconds': expires_in
        })


class VerifyTouristIDAPIView(APIView):
    """
    Law Enforcement / Checkpoint Verification Endpoint.
    Accepts raw scanned JSON payload, URL token, or manual ID + TOTP.
    Validates cryptographic authenticity against database records and logs verification event.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        scanned_data = request.data.get('qr_data')
        id_number = request.data.get('id_number')
        totp_code = request.data.get('totp_code')
        verifier_name = request.data.get('verifier_name', 'Inspector V. Naik')
        verifier_role = request.data.get('verifier_role', 'Tourism Police')
        location_name = request.data.get('location_name', 'Calangute North Checkpoint')

        # Parse JSON string if raw QR data was passed
        if scanned_data:
            if isinstance(scanned_data, str):
                try:
                    scanned_data = json.loads(scanned_data)
                except Exception:
                    # Check if scanned data was a URL
                    if 'id=' in scanned_data:
                        from urllib.parse import urlparse, parse_qs
                        parsed = parse_qs(urlparse(scanned_data).query)
                        id_number = parsed.get('id', [id_number])[0]
                        totp_code = parsed.get('token', [totp_code])[0]
            if isinstance(scanned_data, dict):
                id_number = scanned_data.get('v_id', id_number)
                totp_code = scanned_data.get('totp', totp_code)

        if not id_number:
            return api_response(success=False, message="Digital ID Number required", http_code=status.HTTP_400_BAD_REQUEST)

        # Normalize ID number
        id_number = str(id_number).strip().upper()

        try:
            digital_id = DigitalTouristID.objects.get(id_number=id_number)
        except DigitalTouristID.DoesNotExist:
            return api_response(
                success=False,
                message=f"No active record found for ID '{id_number}' in national database.",
                data={'verification_result': 'INVALID_ID', 'is_genuine': False},
                http_code=status.HTTP_404_NOT_FOUND
            )

        tourist = digital_id.tourist
        user = tourist.user

        # Token Validation (if TOTP code provided)
        is_token_valid = True
        if totp_code:
            is_token_valid = verify_dynamic_totp_token(digital_id.verification_token_secret, str(totp_code).strip(), step=30, window=2)

        # Status & Validity Evaluation
        if digital_id.status == 'FLAGGED':
            verification_result = 'FLAGGED_ALERT'
        elif digital_id.status == 'SUSPENDED':
            verification_result = 'SUSPENDED'
        elif not digital_id.is_valid():
            verification_result = 'EXPIRED'
        elif not is_token_valid:
            verification_result = 'INVALID_TOKEN'
        else:
            verification_result = 'VALID'

        # Audit Log Entry
        log = IDVerificationLog.objects.create(
            digital_id=digital_id,
            verifier_name=verifier_name,
            verifier_role=verifier_role,
            location_name=location_name,
            status_result=verification_result,
            verification_notes=f"Checkpoint scan: {location_name}. Token valid: {is_token_valid}"
        )

        response_data = {
            'id_number': digital_id.id_number,
            'tourist_name': user.get_full_name() or user.username,
            'nationality': tourist.nationality,
            'blood_group': tourist.blood_group or 'Not Specified',
            'hotel_stay_details': tourist.hotel_stay_details or 'Goa Tourism Area',
            'valid_until': digital_id.valid_until.strftime("%Y-%m-%d"),
            'status': digital_id.status,
            'verification_result': verification_result,
            'is_genuine': verification_result in ['VALID', 'FLAGGED_ALERT'],
            'token_verified': is_token_valid,
            'emergency_contacts': [
                {'name': c.name, 'phone': c.phone_number, 'rel': c.relationship}
                for c in user.emergency_contacts.all()
            ],
            'verified_at': log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }

        return api_response(
            success=verification_result == 'VALID',
            message=f"Digital Tourist ID verified: {verification_result}",
            data=response_data
        )


class DigitalIDLogsAPIView(APIView):
    """Returns verification scan logs for a tourist or C2 authority."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_authority:
            logs = IDVerificationLog.objects.all()[:50]
        else:
            profile = getattr(request.user, 'tourist_profile', None)
            if not profile:
                return api_response(success=True, data=[])
            digital_id = getattr(profile, 'digital_id', None)
            logs = digital_id.verification_logs.all() if digital_id else []

        from .serializers import IDVerificationLogSerializer
        return api_response(success=True, data=IDVerificationLogSerializer(logs, many=True).data)
