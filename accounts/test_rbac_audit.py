"""
Automated checks for roles, permissions, audit log and filters.

Run with:   python manage.py test accounts

The tests use only the local (SQLite) database. The AdventureWorks queries
are replaced with fake data, so no SQL Server is needed to run them.
"""
from unittest.mock import patch

from django.contrib.admin.sites import site as admin_site
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from audit.models import AuditEvent
from audit.services import record
from reports.views import ReportView

from .models import Role, User

A = AuditEvent.Action
PASSWORD = "Str0ng-Pass-9876!"
MODULES = ["sales", "customer", "revenue", "cost"]
FAKE_REPORT = {"kpis": [], "charts": [],
               "tables": [{"title": "t", "columns": [], "rows": []}]}


class BaseCase(TestCase):
    databases = {"default"}          # never touch AdventureWorks in tests

    @classmethod
    def setUpTestData(cls):
        def make(username, role, dept=""):
            return User.objects.create_user(
                username=username, password=PASSWORD, role=role, department=dept)

        cls.admin = make("t_admin", Role.ADMIN)
        cls.sales_mgr = make("t_sales_mgr", Role.MANAGER, "sales")
        cls.sales_sup = make("t_sales_sup", Role.SUPERVISOR, "sales")
        cls.sales_emp = make("t_sales_emp", Role.EMPLOYEE, "sales")
        cls.cost_mgr = make("t_cost_mgr", Role.MANAGER, "cost")
        cls.cost_emp = make("t_cost_emp", Role.EMPLOYEE, "cost")

    def setUp(self):
        # Replace the AdventureWorks queries and the template rendering
        self.report_mocks = {}
        for name in MODULES:
            p = patch(f"reports.services.{name}.get_report_data",
                      return_value=FAKE_REPORT)
            self.report_mocks[name] = p.start()
            self.addCleanup(p.stop)
        p = patch("reports.views.get_available_years",
                  return_value=[2011, 2012, 2013, 2014])
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(ReportView, "render_to_response",
                         lambda self, context, **kw: HttpResponse("ok"))
        p.start()
        self.addCleanup(p.stop)

    def url(self, module):
        return reverse(f"reports:{module}")


class LoginTests(BaseCase):
    def test_anonymous_is_redirected_to_login(self):
        resp = self.client.get(self.url("sales"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_valid_login_is_audited(self):
        resp = self.client.post(reverse("accounts:login"),
                                {"username": "t_sales_emp", "password": PASSWORD})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(AuditEvent.objects.filter(
            action=A.LOGIN, actor=self.sales_emp).exists())

    def test_wrong_password_is_audited(self):
        resp = self.client.post(reverse("accounts:login"),
                                {"username": "t_sales_emp", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)       # form shown again
        self.assertTrue(AuditEvent.objects.filter(
            action=A.LOGIN_FAILED, actor_username="t_sales_emp").exists())

    def test_logout_is_audited(self):
        self.client.force_login(self.sales_emp)
        self.client.post(reverse("accounts:logout"))
        self.assertTrue(AuditEvent.objects.filter(
            action=A.LOGOUT, actor=self.sales_emp).exists())

    def test_inactive_user_cannot_log_in(self):
        User.objects.filter(pk=self.sales_emp.pk).update(is_active=False)
        self.assertFalse(self.client.login(username="t_sales_emp", password=PASSWORD))


class ReportAccessTests(BaseCase):
    def test_department_matrix(self):
        allowed = {
            self.admin: set(MODULES),
            self.sales_mgr: {"sales"},
            self.sales_sup: {"sales"},
            self.sales_emp: {"sales"},
            self.cost_mgr: {"cost"},
            self.cost_emp: {"cost"},
        }
        for user, modules in allowed.items():
            self.client.force_login(user)
            for module in MODULES:
                with self.subTest(user=user.username, module=module):
                    expected = 200 if module in modules else 403
                    self.assertEqual(self.client.get(self.url(module)).status_code,
                                     expected)

    def test_direct_url_to_other_department_is_forbidden(self):
        self.client.force_login(self.sales_emp)
        self.assertEqual(self.client.get("/cost/").status_code, 403)

    def test_pdf_export_follows_the_same_rule(self):
        self.client.force_login(self.sales_emp)
        resp = self.client.post("/cost/pdf/", data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_dashboard_lists_only_permitted_reports(self):
        self.client.force_login(self.sales_emp)
        self.assertEqual(self.client.get(reverse("reports:dashboard"))
                         .context["modules"], ["sales"])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("reports:dashboard"))
                         .context["modules"], MODULES)


class YearFilterTests(BaseCase):
    def test_invalid_year_falls_back_to_all_years(self):
        self.client.force_login(self.sales_emp)
        resp = self.client.get(self.url("sales") + "?start_year=abc&end_year=xyz")
        self.assertEqual(resp.status_code, 200)
        self.report_mocks["sales"].assert_called_once_with(2011, 2014)

    def test_valid_range_is_used(self):
        self.client.force_login(self.sales_emp)
        self.client.get(self.url("sales") + "?start_year=2012&end_year=2013")
        self.report_mocks["sales"].assert_called_once_with(2012, 2013)

    def test_reversed_range_is_swapped(self):
        self.client.force_login(self.sales_emp)
        self.client.get(self.url("sales") + "?start_year=2014&end_year=2012")
        self.report_mocks["sales"].assert_called_once_with(2012, 2014)


class TeamManagementTests(BaseCase):
    def test_team_list_by_role(self):
        for user, status in [(self.sales_mgr, 200), (self.sales_sup, 200),
                             (self.sales_emp, 403)]:
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(
                    self.client.get(reverse("accounts:team_list")).status_code, status)

    def test_only_manager_can_open_the_create_form(self):
        for user, status in [(self.sales_mgr, 200), (self.sales_sup, 403),
                             (self.sales_emp, 403)]:
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(
                    self.client.get(reverse("accounts:team_create")).status_code, status)

    def test_supervisor_cannot_create_users(self):
        before = User.objects.count()
        self.client.force_login(self.sales_sup)
        resp = self.client.post(reverse("accounts:team_create"), {
            "username": "t_new", "password1": PASSWORD, "password2": PASSWORD})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(User.objects.count(), before)

    def test_manager_creates_employee_in_own_department_and_it_is_audited(self):
        self.client.force_login(self.sales_mgr)
        resp = self.client.post(reverse("accounts:team_create"), {
            "username": "t_new_emp", "first_name": "New", "last_name": "Emp",
            "email": "new@example.com", "password1": PASSWORD, "password2": PASSWORD})
        self.assertEqual(resp.status_code, 302)
        new = User.objects.get(username="t_new_emp")
        self.assertEqual((new.role, new.department), (Role.EMPLOYEE, "sales"))
        self.assertTrue(AuditEvent.objects.filter(
            action=A.USER_CREATED, actor=self.sales_mgr,
            target_username="t_new_emp").exists())

    def test_manager_cannot_touch_another_departments_employee(self):
        self.client.force_login(self.sales_mgr)
        edit = reverse("accounts:team_edit", args=[self.cost_emp.pk])
        toggle = reverse("accounts:team_toggle", args=[self.cost_emp.pk])
        self.assertEqual(self.client.get(edit).status_code, 404)
        self.assertEqual(self.client.post(toggle).status_code, 404)
        self.cost_emp.refresh_from_db()
        self.assertTrue(self.cost_emp.is_active)

    def test_manager_deactivates_and_reactivates_employee_with_audit(self):
        self.client.force_login(self.sales_mgr)
        toggle = reverse("accounts:team_toggle", args=[self.sales_emp.pk])
        self.client.post(toggle)
        self.sales_emp.refresh_from_db()
        self.assertFalse(self.sales_emp.is_active)
        self.assertTrue(AuditEvent.objects.filter(
            action=A.USER_DEACTIVATED, target_username="t_sales_emp").exists())
        self.client.post(toggle)
        self.sales_emp.refresh_from_db()
        self.assertTrue(self.sales_emp.is_active)
        self.assertTrue(AuditEvent.objects.filter(
            action=A.USER_REACTIVATED, target_username="t_sales_emp").exists())

    def test_employee_cannot_edit_anyone(self):
        self.client.force_login(self.sales_emp)
        edit = reverse("accounts:team_edit", args=[self.sales_emp.pk])
        self.assertEqual(self.client.get(edit).status_code, 403)


class AuditLogTests(BaseCase):
    def test_report_view_is_audited(self):
        self.client.force_login(self.sales_emp)
        self.client.get(self.url("sales"))
        self.assertEqual(AuditEvent.objects.filter(
            action=A.REPORT_VIEWED, actor=self.sales_emp, department="sales").count(), 1)

    def test_access_denied_is_audited(self):
        self.client.force_login(self.sales_emp)
        self.client.get("/cost/")
        event = AuditEvent.objects.get(action=A.ACCESS_DENIED, actor=self.sales_emp)
        self.assertEqual(event.detail["path"], "/cost/")

    def test_audit_page_access_by_role(self):
        for user, status in [(self.admin, 200), (self.sales_mgr, 200),
                             (self.sales_sup, 403), (self.sales_emp, 403)]:
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(reverse("audit:log")).status_code,
                                 status)

    def test_manager_sees_only_own_department(self):
        record(self.sales_mgr, A.REPORT_VIEWED, department="sales", detail={"report": "sales"})
        record(self.cost_mgr, A.REPORT_VIEWED, department="cost", detail={"report": "cost"})
        self.client.force_login(self.sales_mgr)
        events = self.client.get(reverse("audit:log")).context["events"]
        departments = {e.department for e in events}
        self.assertIn("sales", departments)
        self.assertNotIn("cost", departments)

    def test_admin_sees_all_departments(self):
        record(self.sales_mgr, A.REPORT_VIEWED, department="sales", detail={"report": "sales"})
        record(self.cost_mgr, A.REPORT_VIEWED, department="cost", detail={"report": "cost"})
        self.client.force_login(self.admin)
        events = self.client.get(reverse("audit:log")).context["events"]
        self.assertTrue({"sales", "cost"} <= {e.department for e in events})

    def test_entries_cannot_be_edited(self):
        event = record(self.sales_mgr, A.REPORT_VIEWED, department="sales")
        event.detail = {"changed": True}
        with self.assertRaises(ValueError):
            event.save()

    def test_admin_site_cannot_change_or_delete_entries(self):
        model_admin = admin_site._registry[AuditEvent]
        request = RequestFactory().get("/")
        request.user = self.admin
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        self.assertFalse(model_admin.has_add_permission(request))