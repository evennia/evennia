"""
Sets up an api-access permission check using the in-game permission hierarchy.

"""


from django.conf import settings
from rest_framework import permissions

from evennia.locks.lockhandler import check_perm


class EvenniaPermission(permissions.BasePermission):
    """
    A Django Rest Framework permission class that allows us to use Evennia's
    permission structure. Based on the action in a given view, we'll check a
    corresponding Evennia access/lock check.

    """

    # subclass this to change these permissions
    MINIMUM_LIST_PERMISSION = settings.REST_FRAMEWORK.get("DEFAULT_LIST_PERMISSION", "builder")
    MINIMUM_CREATE_PERMISSION = settings.REST_FRAMEWORK.get("DEFAULT_CREATE_PERMISSION", "builder")
    view_locks = settings.REST_FRAMEWORK.get("DEFAULT_VIEW_LOCKS", ["examine"])
    destroy_locks = settings.REST_FRAMEWORK.get("DEFAULT_DESTROY_LOCKS", ["delete"])
    update_locks = settings.REST_FRAMEWORK.get("DEFAULT_UPDATE_LOCKS", ["control", "edit"])

    def has_permission(self, request, view):
        """Checks for permissions

        Args:
            request (Request): The incoming request object.
            view (View): The django view we are checking permission for.

        Returns:
            bool: If permission is granted or not. If we return False here, a PermissionDenied
            error will be raised from the view.

        Notes:
            This method is a check that always happens first. If there's an object involved,
            such as with retrieve, update, or delete, then the has_object_permission method
            is called after this, assuming this returns `True`.
        """
        # Only allow authenticated users to call the API
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        # these actions don't support object-level permissions, so use the above definitions
        if view.action == "list":
            return check_perm(request.user, self.MINIMUM_LIST_PERMISSION)
        if view.action == "create":
            return check_perm(request.user, self.MINIMUM_CREATE_PERMISSION)
        return True  # this means we'll check object-level permissions

    @staticmethod
    def check_locks(obj, user, locks):
        """Checks access for user for object with given locks
        Args:
            obj: Object instance we're checking
            user (Account): User who we're checking permissions
            locks (list): list of lockstrings

        Returns:
            bool: True if they have access, False if they don't
        """
        return any([obj.access(user, lock) for lock in locks])

    def has_object_permission(self, request, view, obj):
        """Checks object-level permissions after has_permission

        Args:
            request (Request): The incoming request object.
            view (View): The django view we are checking permission for.
            obj: Object we're checking object-level permissions for

        Returns:
            bool: If permission is granted or not. If we return False here, a PermissionDenied
            error will be raised from the view.

        Notes:
            This method assumes that has_permission has already returned True. We check
            equivalent Evennia permissions in the request.user to determine if they can
            complete the action.
        """
        if view.action in ("list", "retrieve"):
            # access_type is based on the examine command
            return self.check_locks(obj, request.user, self.view_locks)
        if view.action == "destroy":
            # access type based on the destroy command
            return self.check_locks(obj, request.user, self.destroy_locks)
        if view.action in ("update", "partial_update", "set_attribute"):
            # access type based on set command
            return self.check_locks(obj, request.user, self.update_locks)
