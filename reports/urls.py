from django.urls import path
from . import views

app_name = "reports"
urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("sales/", views.SalesReportView.as_view(), name="sales"),
    path("customer/", views.CustomerReportView.as_view(), name="customer"),
    path("revenue/", views.RevenueReportView.as_view(), name="revenue"),
    path("cost/", views.CostReportView.as_view(), name="cost"),
]
