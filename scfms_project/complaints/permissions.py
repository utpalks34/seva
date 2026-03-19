# complaints/permissions.py

from rest_framework.permissions import BasePermission

class IsPublicCitizen(BasePermission):
    """
    Allows access only to authenticated users with the 'PC' role.
    """
    message = 'Access denied. Only Public Citizens can perform this action.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'PC')

class IsGovernmentOfficial(BasePermission):
    """
    Allows access only to authenticated users with the 'GO' role.
    """
    message = 'Access denied. Only Government Officials can perform this action.'

    def has_permission(self, request, view):
        # We can use is_staff for GOs as well, or just rely on the 'role' field
        return bool(request.user and request.user.is_authenticated and request.user.role == 'GO')