from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_admin_or_staff_user(user):
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, "role", None) in {"admin", "staff"}
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        )
    )


class IsAdminOrStaff(BasePermission):
    def has_permission(self, request, view):
        return is_admin_or_staff_user(request.user)


class ReadOnlyOrAdminStaff(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_admin_or_staff_user(request.user)


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "customer")
