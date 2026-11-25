from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User
from audit.models import AuditEvent
from audit.services import changes_from_form, record

A = AuditEvent.Action

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Access", {"fields": ("role", "department")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (("Access", {"fields": ("role", "department")}),)
    list_display = ("username", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            if form.has_changed():
                record(request.user, A.USER_UPDATED, department=obj.department,
                       target=obj, request=request,
                       detail={"via": "admin", "changes": changes_from_form(form)})
        else:
            record(request.user, A.USER_CREATED, department=obj.department,
                   target=obj, request=request,
                   detail={"via": "admin", "role": obj.role,
                           "department": obj.department})

    def delete_model(self, request, obj):
        record(request.user, A.USER_DELETED, department=obj.department,
               target=obj, request=request, detail={"via": "admin"})
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):   # the bulk "delete selected" action
        for obj in queryset:
            record(request.user, A.USER_DELETED, department=obj.department,
                   target=obj, request=request, detail={"via": "admin"})
        super().delete_queryset(request, queryset)
