from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class Department(models.TextChoices):
    SALES = "sales", "Sales"
    CUSTOMER = "customer", "Customer"
    REVENUE = "revenue", "Revenue"
    COST = "cost", "Cost"

class Role(models.TextChoices):
    ADMIN = "admin", "Administrator"
    MANAGER = "manager", "Manager"
    EMPLOYEE = "employee", "Employee"

class User(AbstractUser):
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.CharField(max_length=10, choices=Department.choices, blank=True)

    def save(self, *args, **kwargs):
        # Keep role the single source of truth (also covers `createsuperuser`)
        if self.is_superuser:
            self.role = Role.ADMIN
        if self.role == Role.ADMIN:
            self.is_staff = self.is_superuser = True
            self.department = ""        # admins aren't tied to one department
        super().save(*args, **kwargs)
