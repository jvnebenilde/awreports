from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.views.generic import ListView
from accounts.models import Role
from .models import AuditEvent

# Create your views here.

class AuditLogView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "audit/log.html"
    context_object_name = "events"
    paginate_by = 50

    def test_func(self):
        u = self.request.user
        return u.is_active and u.role in (Role.MANAGER, Role.ADMIN)

    def get_queryset(self):
        user = self.request.user
        qs = AuditEvent.objects.all()
        if user.role == Role.MANAGER:
            qs = qs.filter(department=user.department)      # the scoping rule

        self.current_view = self.request.GET.get("view", "all")
        if self.current_view == "reports":
            qs = qs.filter(action=AuditEvent.Action.REPORT_PRINTED)
        elif self.current_view == "accounts":
            qs = qs.filter(action__in=AuditEvent.USER_ACTIONS)
        elif self.current_view == "managers" and user.role == Role.ADMIN:
            qs = qs.filter(action=AuditEvent.Action.USER_CREATED,
                           target_role=Role.MANAGER)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_view"] = self.current_view
        if self.current_view == "managers" and self.request.user.role == Role.ADMIN:
            ctx["creator_counts"] = (
                self.object_list.values("actor_username")
                .annotate(n=Count("pk")).order_by("-n")
            )
        return ctx

