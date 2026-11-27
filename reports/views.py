import json
import weasyprint
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView
from accounts.mixins import ModuleAccessMixin
from accounts.permissions import accessible_modules
from audit.models import AuditEvent
from audit.services import record
from .services import sales, customer, revenue, cost
from .services.db import get_available_years

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "reports/dashboard.html"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["modules"] = accessible_modules(self.request.user)
        return ctx


class ReportView(ModuleAccessMixin, TemplateView):
    template_name = "reports/report.html"
    service_module = None

    def get_year_range(self, years):
        min_y, max_y = min(years), max(years)
        try:
            start_year = int(self.request.GET.get("start_year", min_y))
            end_year = int(self.request.GET.get("end_year", max_y))
        except ValueError:
            start_year, end_year = min_y, max_y
        if start_year > end_year:
            start_year, end_year = end_year, start_year
        return start_year, end_year

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        years = get_available_years()
        start_year, end_year = self.get_year_range(years)
        report_data = self.service_module.get_report_data(start_year, end_year)
        total_rows = sum(len(t["rows"]) for t in report_data["tables"])
        ctx.update(
            module=self.module,
            years=years,
            start_year=start_year,
            end_year=end_year,
            report_data=report_data,
            total_rows=total_rows,
        )
        return ctx


class SalesReportView(ReportView):
    module = "sales"
    service_module = sales
    template_name = "reports/sales.html"


class CustomerReportView(ReportView):
    module = "customer"
    service_module = customer
    template_name = "reports/customer.html"


class RevenueReportView(ReportView):
    module = "revenue"
    service_module = revenue
    template_name = "reports/revenue.html"


class CostReportView(ReportView):
    module = "cost"
    service_module = cost
    template_name = "reports/cost.html"

MODULE_SERVICES = {
    "sales": sales,
    "customer": customer,
    "revenue": revenue,
    "cost": cost,
}


class ExportPdfView(ModuleAccessMixin, View):
    """Logs REPORT_PRINTED and renders a clean WeasyPrint PDF with embedded chart images."""

    def dispatch(self, request, *args, **kwargs):
        self.module = kwargs.get("module", "")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, module):
        service_mod = MODULE_SERVICES.get(module)
        if not service_mod:
            return JsonResponse({"error": "Unknown report module"}, status=400)

        try:
            body = json.loads(request.body or "{}")
            start_year = int(body.get("start_year"))
            end_year = int(body.get("end_year"))
            chart_images = body.get("charts", [])  # list of {"title": ..., "data_url": ...}
        except (ValueError, TypeError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid request payload"}, status=400)

        if start_year > end_year:
            start_year, end_year = end_year, start_year

        report_data = service_mod.get_report_data(start_year, end_year)
        total_rows = sum(len(t["rows"]) for t in report_data["tables"])

        # 1. Record the print event in the audit log
        record(
            actor=request.user,
            action=AuditEvent.Action.REPORT_PRINTED,
            department=module,
            detail={
                "report": module,
                "start_year": start_year,
                "end_year": end_year,
                "rows": total_rows,
            },
            request=request,
        )

        # 2. Format the account display name of the user who printed it
        full_name = request.user.get_full_name().strip()
        printed_by = f"{full_name} ({request.user.username})" if full_name else request.user.username

        # 3. Render dedicated PDF HTML and compile with WeasyPrint
        html_string = render_to_string(
            "reports/pdf_report.html",
            {
                "module": module,
                "start_year": start_year,
                "end_year": end_year,
                "report_data": report_data,
                "chart_images": chart_images,
                "printed_by": printed_by,
            },
            request=request,
        )

        pdf_bytes = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()

        filename = f"{module}_report_{start_year}_{end_year}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

