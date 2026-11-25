from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from audit.models import AuditEvent
from audit.services import changes_from_form, record
from .forms import EmployeeCreateForm, EmployeeUpdateForm
from .mixins import ManagerRequiredMixin
from .models import Role, User

A = AuditEvent.Action

# Create your views here.

class TeamScopedMixin(ManagerRequiredMixin):
    def get_queryset(self):
        return User.objects.filter(
            role=Role.EMPLOYEE, department=self.request.user.department
        )

class TeamListView(TeamScopedMixin, ListView):
    template_name = "accounts/team_list.html"
    context_object_name = "employees"

class TeamCreateView(ManagerRequiredMixin, CreateView):
    form_class = EmployeeCreateForm
    template_name = "accounts/team_form.html"
    success_url = reverse_lazy("accounts:team_list")

    def form_valid(self, form):
        form.instance.role = Role.EMPLOYEE
        form.instance.department = self.request.user.department
        return super().form_valid(form)

class TeamUpdateView(TeamScopedMixin, UpdateView):
    form_class = EmployeeUpdateForm
    template_name = "accounts/team_form.html"
    success_url = reverse_lazy("accounts:team_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.has_changed():
            record(self.request.user, A.USER_UPDATED,
                   department=self.object.department, target=self.object,
                   detail={"via": "team", "changes": changes_from_form(form)},
                   request=self.request)
        return response

class TeamToggleActiveView(TeamScopedMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(self.get_queryset(), pk=pk)  # 404 outside their team
        employee.is_active = not employee.is_active
        employee.save(update_fields=["is_active"])
        return redirect("accounts:team_list")
