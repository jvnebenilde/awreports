"""Create (or reset) the demo accounts so the system is ready to present.

Usage:  python manage.py seed_demo
Safe to run many times: existing demo users are updated, not duplicated.
All demo accounts share the password below. Demo use only.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

PASSWORD = "Demo@12345"

# (username, role, department)
DEMO_USERS = [
    ("admin",          "admin",      ""),
    ("sales.manager",  "manager",    "sales"),
    ("sales.super",    "supervisor", "sales"),
    ("sales.emp",      "employee",   "sales"),
    ("cust.manager",   "manager",    "customer"),
    ("cust.super",     "supervisor", "customer"),
    ("cust.emp",       "employee",   "customer"),
    ("rev.manager",    "manager",    "revenue"),
    ("rev.super",      "supervisor", "revenue"),
    ("rev.emp",        "employee",   "revenue"),
    ("cost.manager",   "manager",    "cost"),
    ("cost.super",     "supervisor", "cost"),
    ("cost.emp",       "employee",   "cost"),
]


class Command(BaseCommand):
    help = "Create or reset demo users for every role and department."

    def handle(self, *args, **options):
        User = get_user_model()
        for username, role, dept in DEMO_USERS:
            user, created = User.objects.get_or_create(username=username)
            user.role = role
            user.department = dept
            user.is_active = True
            user.is_superuser = role == "admin"
            user.is_staff = role == "admin"
            user.set_password(PASSWORD)
            user.save()
            self.stdout.write(f"{'created' if created else 'updated'}: {username:15} {role:11} {dept or '-'}")
        self.stdout.write(self.style.SUCCESS(f"\nDone. Password for all demo accounts: {PASSWORD}"))