from .models import Department, Role

MODULES = [d.value for d in Department]

def can_view_module(user, module):
    return (
        user.is_authenticated and user.is_active
        and (user.role == Role.ADMIN or user.department == module)
    )

def accessible_modules(user):
    return [m for m in MODULES if can_view_module(user, m)]
