# complaints/permissions.py

from rest_framework.permissions import BasePermission

class IsPublicCitizen(BasePermission):
    """
    Allows access only to authenticated users with the 'PC' role.
    """
    message = 'Access denied. Only Public Citizens can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.role == 'PC'
            and request.user.is_verified
        )

class IsGovernmentOfficial(BasePermission):
    """
    Allows access only to authenticated users with the 'GO' role.
    """
    message = 'Access denied. Only Government Officials can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.role in {'GO', 'AD'}
            and request.user.is_verified
        )


class IsAdminRole(BasePermission):
    message = 'Access denied. Only administrators can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.role == 'AD'
            and request.user.is_staff
        )
