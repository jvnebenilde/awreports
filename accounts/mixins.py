from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Role
from .permissions import can_view_module

# Functions for checking user credentials based on department and position
class ModuleAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Set `module = "sales"` etc. on the view."""
    module = None
    def test_func(self):
        return can_view_module(self.request.user, self.module)

class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_active and u.role == Role.MANAGER
