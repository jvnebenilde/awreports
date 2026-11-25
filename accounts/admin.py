from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Access", {"fields": ("role", "department")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (("Access", {"fields": ("role", "department")}),)
    list_display = ("username", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")
