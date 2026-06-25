# api/permissions.py
from rest_framework import permissions


class IsStaffOrApprovedAgent(permissions.BasePermission):
    """
    Read access for everyone. Write access only for staff/admin or an
    approved agent (via AgentProfile.is_approved).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return (
            hasattr(request.user, 'agent_profile')
            and request.user.agent_profile.is_approved
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        # An approved agent can only modify their own listings.
        return (
            hasattr(request.user, 'agent_profile')
            and request.user.agent_profile.is_approved
            and obj.agent_id == request.user.agent_profile.id
        )


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Anyone can read. Only staff/admin can write.
    Used for LandBankingPlan — pricing/terms should never be publicly editable.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class InquiryPermission(permissions.BasePermission):
    """
    - Anyone (including anonymous) can submit an inquiry (create).
    - Only staff, or the agent who owns the listing, can update/delete an
      inquiry. The original submitter (even if authenticated) cannot edit
      it after the fact — inquiry status is a back-office concern.
    - Read access requires authentication (inquiries contain contact info).
    """

    def has_permission(self, request, view):
        if view.action == 'create':
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        if request.user.is_staff:
            return True
        return (
            hasattr(request.user, 'agent_profile')
            and request.user.agent_profile.is_approved
            and obj.property_listing.agent_id == request.user.agent_profile.id
        )


class IsStaffOnly(permissions.BasePermission):
    """Used where write access should never be exposed to ordinary users —
    e.g. creating Payment records directly (must go through make_payment)."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)