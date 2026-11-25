from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from accounts.mixins import ModuleAccessMixin
from accounts.permissions import accessible_modules
from .services import sales, customer, revenue, cost

# Create your views here.
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "reports/dashboard.html"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["modules"] = accessible_modules(self.request.user)   # only show allowed links
        return ctx

class ReportView(ModuleAccessMixin, TemplateView):
    template_name = "reports/report.html"
    def get_rows(self):
        raise NotImplementedError
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(module=self.module, rows=self.get_rows())
        return ctx

class SalesReportView(ReportView):
    module = "sales"
    def get_rows(self):
        return sales.monthly_sales()

class CustomerReportView(ReportView):
    module = "customer"
    def get_rows(self): return customer.top_customers()

class RevenueReportView(ReportView):
    module = "revenue"
    def get_rows(self): return revenue.revenue_by_territory()

class CostReportView(ReportView):
    module = "cost"
    def get_rows(self): return cost.vendor_purchase_costs()
