from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from rest_framework.permissions import BasePermission


# ==============================================================================
# Django REST Framework Role-Based Permissions
# ==============================================================================

class IsTourist(BasePermission):
    """Allows access only to authenticated users with the TOURIST role."""
    message = "Access restricted to registered tourists only."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_tourist)


class IsAuthority(BasePermission):
    """Allows access to authenticated users with AUTHORITY, OPERATOR, RESPONDER, or ADMIN roles."""
    message = "Access restricted to verified authority and response personnel only."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_authority)


class IsTourismAdmin(BasePermission):
    """Allows access strictly to Tourism Administrators and Superusers."""
    message = "Access restricted to Tourism Department Administrators only."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_tourism_admin)


# ==============================================================================
# Standard Django View Decorators
# ==============================================================================

def tourist_required(view_func):
    """
    Decorator for views that checks if the user is logged in and is a Tourist.
    Redirects unauthenticated users to login, and raises PermissionDenied for non-tourists.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to access the tourist safety portal.")
            return redirect('accounts:login')
        if not request.user.is_tourist:
            # If an operator visits tourist view, optionally permit or redirect to C2
            if request.user.is_authority:
                return redirect('dashboard:c2_command')
            raise PermissionDenied("Access denied. This page is reserved for registered tourists.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def authority_required(view_func):
    """
    Decorator for views that checks if the user is logged in and has an Authority role.
    Redirects unauthenticated users to login, and raises PermissionDenied (403) for regular tourists.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Official authorization required. Please log in.")
            return redirect('accounts:login')
        if not request.user.is_authority:
            raise PermissionDenied("Access forbidden. You do not have official authority credentials to view this tactical dashboard.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def tourism_admin_required(view_func):
    """
    Decorator for views that checks if the user is logged in and is a Tourism Administrator.
    Redirects unauthenticated users to login, and raises PermissionDenied (403) for tourists and standard operators.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Administrator authentication required.")
            return redirect('accounts:login')
        if not request.user.is_tourism_admin:
            raise PermissionDenied("Access forbidden. Only authorized Tourism Administrators can access this administration portal.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ==============================================================================
# View Mixins for Class-Based Views
# ==============================================================================

class TouristRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_tourist:
            raise PermissionDenied("Tourist role required.")
        return super().dispatch(request, *args, **kwargs)


class AuthorityRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_authority:
            raise PermissionDenied("Authority credentials required.")
        return super().dispatch(request, *args, **kwargs)


class TourismAdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_tourism_admin:
            raise PermissionDenied("Tourism Administrator credentials required.")
        return super().dispatch(request, *args, **kwargs)
