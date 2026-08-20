import uuid
import secrets
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from common.utils import api_response, generate_secure_crypto_hash
from .models import User, EmergencyContact
from .forms import (
    TouristRegistrationForm,
    AuthorityRegistrationForm,
    LoginForm,
    UserProfileUpdateForm,
    EmergencyContactForm
)
from .serializers import UserSerializer, EmergencyContactSerializer
from .permissions import IsTourist, IsAuthority, IsTourismAdmin, tourism_admin_required


def register_view(request):
    """Tourist Self-Registration Portal."""
    if request.user.is_authenticated:
        if request.user.is_tourism_admin:
            return redirect('accounts:admin_portal')
        elif request.user.is_authority:
            return redirect('dashboard:c2_command')
        return redirect('tourists:home')

    if request.method == 'POST':
        form = TouristRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'TOURIST'
            user.is_verified = True
            user.save()

            # Create Emergency Contact
            ec_name = form.cleaned_data.get('emergency_contact_name')
            ec_phone = form.cleaned_data.get('emergency_contact_phone')
            ec_rel = form.cleaned_data.get('emergency_contact_relation')
            if ec_name and ec_phone:
                EmergencyContact.objects.create(
                    user=user,
                    name=ec_name,
                    phone_number=ec_phone,
                    relationship=ec_rel,
                    is_primary=True
                )

            # Lazy import to avoid circular dependencies
            from tourists.models import TouristProfile
            from digital_id.models import DigitalTouristID
            from risk.models import TouristRiskAssessment

            # Create Tourist Profile
            profile = TouristProfile.objects.create(
                user=user,
                nationality=form.cleaned_data.get('nationality', 'Indian'),
                blood_group=form.cleaned_data.get('blood_group', ''),
                hotel_stay_details=form.cleaned_data.get('hotel_stay_details', ''),
                trip_start_date=timezone.now().date(),
                trip_end_date=timezone.now().date() + timedelta(days=14),
                trip_status='ACTIVE',
                current_latitude=15.4989,  # Default demo latitude (Panaji / Goa)
                current_longitude=73.8278,
                last_location_time=timezone.now(),
                battery_level=100
            )

            # Generate Digital Tourist ID
            id_code = f"VGL-{timezone.now().year}-{secrets.token_hex(3).upper()}"
            secret_seed = secrets.token_hex(16)
            crypto_signature = generate_secure_crypto_hash(f"{user.username}:{id_code}:{secret_seed}")

            digital_id = DigitalTouristID.objects.create(
                tourist=profile,
                id_number=id_code,
                crypto_hash=crypto_signature,
                status='ACTIVE',
                valid_until=timezone.now() + timedelta(days=30),
                verification_token_secret=secret_seed
            )
            digital_id.generate_qr_code()

            # Baseline Risk Assessment
            TouristRiskAssessment.objects.create(
                tourist=profile,
                overall_score=12,
                risk_level='SAFE',
                spatial_risk_score=10,
                temporal_risk_score=10,
                isolation_risk_score=15,
                crowd_risk_score=10,
                device_health_score=5,
                primary_risk_factor="Normal Tourist Hub activity",
                ai_recommendation="Area has strong tourist police presence. Enjoy your visit safely."
            )

            login(request, user)
            messages.success(request, f"Registration complete! Your Digital Tourist ID ({id_code}) is active.")
            return redirect('tourists:home')
    else:
        form = TouristRegistrationForm()

    return render(request, 'auth/register.html', {'form': form})


def register_authority_view(request):
    """Authority & Field Responder Registration Portal."""
    if request.user.is_authenticated:
        if request.user.is_tourism_admin:
            return redirect('accounts:admin_portal')
        elif request.user.is_authority:
            return redirect('dashboard:c2_command')
        return redirect('tourists:home')

    if request.method == 'POST':
        form = AuthorityRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_verified = True
            if user.role == 'ADMIN':
                user.is_staff = True
            user.save()

            login(request, user)
            messages.success(request, f"Official account created. Welcome {user.get_full_name()} ({user.agency_name}).")
            if user.is_tourism_admin:
                return redirect('accounts:admin_portal')
            return redirect('dashboard:c2_command')
    else:
        form = AuthorityRegistrationForm()

    return render(request, 'auth/register_authority.html', {'form': form})


def login_view(request):
    """Unified Role-Aware Login View."""
    if request.user.is_authenticated:
        if request.user.is_tourism_admin:
            return redirect('accounts:admin_portal')
        elif request.user.is_authority:
            return redirect('dashboard:c2_command')
        return redirect('tourists:home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")

            # Role-based Redirection
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            if user.is_tourism_admin:
                return redirect('accounts:admin_portal')
            elif user.is_authority:
                return redirect('dashboard:c2_command')
            return redirect('tourists:home')
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Secure Logout View."""
    logout(request)
    messages.info(request, "You have been securely logged out.")
    return redirect('accounts:login')


@login_required
def profile_management_view(request):
    """Profile settings, emergency contacts, and password change."""
    user = request.user
    profile_form = UserProfileUpdateForm(instance=user)
    password_form = PasswordChangeForm(user=user)
    contact_form = EmergencyContactForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile_form = UserProfileUpdateForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile details updated successfully.")
                return redirect('accounts:profile_management')

        elif action == 'change_password':
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user_updated = password_form.save()
                update_session_auth_hash(request, user_updated)
                messages.success(request, "Password changed successfully.")
                return redirect('accounts:profile_management')
            else:
                messages.error(request, "Please correct the password errors below.")

        elif action == 'add_contact':
            contact_form = EmergencyContactForm(request.POST)
            if contact_form.is_valid():
                contact = contact_form.save(commit=False)
                contact.user = user
                contact.save()
                messages.success(request, f"Emergency contact {contact.name} added.")
                return redirect('accounts:profile_management')

        elif action == 'delete_contact':
            contact_id = request.POST.get('contact_id')
            contact = get_object_or_404(EmergencyContact, id=contact_id, user=user)
            contact.delete()
            messages.info(request, "Emergency contact removed.")
            return redirect('accounts:profile_management')

    contacts = user.emergency_contacts.all()
    return render(request, 'auth/profile_management.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'contact_form': contact_form,
        'contacts': contacts
    })


@tourism_admin_required
def admin_portal_view(request):
    """Tourism Administrator Central Control & RBAC Console."""
    users = User.objects.all().order_by('-date_joined')
    tourists_count = User.objects.filter(role='TOURIST').count()
    authorities_count = User.objects.filter(role__in=['AUTHORITY', 'OPERATOR', 'RESPONDER']).count()
    admins_count = User.objects.filter(role='ADMIN').count()

    from emergency.models import SOSAlert, ResponderUnit
    from geofencing.models import GeoZone, GeofenceBreachLog
    from incidents.models import Incident

    context = {
        'users': users,
        'tourists_count': tourists_count,
        'authorities_count': authorities_count,
        'admins_count': admins_count,
        'active_sos_count': SOSAlert.objects.filter(status__in=['TRIGGERED', 'ACKNOWLEDGED', 'DISPATCHED']).count(),
        'active_zones_count': GeoZone.objects.filter(is_active=True).count(),
        'breaches_count': GeofenceBreachLog.objects.count(),
        'incidents_count': Incident.objects.count(),
        'responders': ResponderUnit.objects.all()
    }
    return render(request, 'authority/admin_portal.html', context)


# ==============================================================================
# REST API Endpoints with Protected RBAC
# ==============================================================================

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return api_response(success=True, message="User profile retrieved", data=serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(success=True, message="User profile updated", data=serializer.data)
        return api_response(success=False, message="Invalid profile data", data=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)


class EmergencyContactsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = request.user.emergency_contacts.all()
        return api_response(success=True, data=EmergencyContactSerializer(contacts, many=True).data)

    def post(self, request):
        serializer = EmergencyContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return api_response(success=True, message="Emergency contact added", data=serializer.data, http_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Invalid contact data", data=serializer.errors, http_code=status.HTTP_400_BAD_REQUEST)


class AdminUserManagementAPIView(APIView):
    permission_classes = [IsTourismAdmin]

    def get(self, request):
        users = User.objects.all().order_by('-date_joined')
        return api_response(success=True, data=UserSerializer(users, many=True).data)

    def patch(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        role = request.data.get('role')
        if role and role in dict(User.ROLE_CHOICES):
            target_user.role = role
            if role == 'ADMIN':
                target_user.is_staff = True
            target_user.save()
            return api_response(success=True, message=f"User {target_user.username} role updated to {role}")
        return api_response(success=False, message="Invalid role provided", http_code=status.HTTP_400_BAD_REQUEST)
