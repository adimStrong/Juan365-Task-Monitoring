from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin users"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsManagerUser(permissions.BasePermission):
    """Allow access to admin and manager users"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_manager


class IsTicketOwnerOrManager(permissions.BasePermission):
    """Allow ticket owner or manager to modify"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_manager:
            return True
        return obj.requester == request.user


class IsTicketParticipant(permissions.BasePermission):
    """Allow ticket participants (requester, assigned, approver) to view/comment"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_manager:
            return True
        return (obj.requester == request.user or
                obj.assigned_to == request.user or
                obj.approver == request.user)


class CanApproveTicket(permissions.BasePermission):
    """Only managers can approve tickets"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_manager
