from django.contrib import admin
from .models import AuditEvent

# Register your models here.
@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor_username", "action", "target_username", "department")
    list_filter = ("action", "department")
    search_fields = ("actor_username", "target_username")

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
