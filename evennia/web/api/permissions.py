from rest_framework import permissions

from django.conf import settings


class EvenniaPermission(permissions.BasePermission):
    """
    A Django Rest Framework permission class that allows us to use
    Evennia's permission structure. Based on the action in a given
    view, we'll check a corresponding Evennia access/lock check.
    """
    # subclass this to change these permissions
    MINIMUM_LIST_PERMISSION = settings.REST_FRAMEWORK["DEFAULT_LIST_PERMISSION"]
    MINIMUM_CREATE_PERMISSION = settings.REST_FRAMEWORK["DEFAULT_CREATE_PERMISSION"]
    view_locks = settings.REST_FRAMEWORK["DEFAULT_VIEW_LOCKS"]
    destroy_locks = settings.REST_FRAMEWORK["DEFAULT_DESTROY_LOCKS"]
    update_locks = settings.REST_FRAMEWORK["DEFAULT_UPDATE_LOCKS"]

    def has_permission(self, request, view):
        """
        This method is a check that always happens first. If there's an object involved,
        such as with retrieve, update, or delete, then the has_object_permission method
        is also called if this returns True. If we return False, a permission denied
        error is raised.
        """
        # Only allow authenticated users to call the API
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        # these actions don't support object-level permissions, so use the above definitions
        if view.action == "list":
            return request.user.has_permistring(self.MINIMUM_LIST_PERMISSION)
        if view.action == "create":
            return request.user.has_permistring(self.MINIMUM_CREATE_PERMISSION)
        return True  # this means we'll check object-level permissions

    @staticmethod
    def check_locks(obj, user, locks):
        return any([obj.access(user, lock) for lock in locks])

    def has_object_permission(self, request, view, obj):
        """
        This method assumes that has_permission has already returned True. We check
        equivalent Evennia permissions in the request.user to determine if they can
        complete the action. If so, we return True. Otherwise we return False, and
        a permission denied error will be raised.
        """
        if request.user.is_superuser:
            return True
        if view.action in ("list", "retrieve"):
            # access_type is based on the examine command
            return self.check_locks(obj, request.user, self.view_locks)
        if view.action == "destroy":
            # access type based on the destroy command
            return self.check_locks(obj, request.user, self.destroy_locks)
        if view.action in ("update", "partial_update"):
            # access type based on set command
            return self.check_locks(obj, request.user, self.update_locks)
