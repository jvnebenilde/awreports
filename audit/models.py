from django.db import models
from django.conf import settings

# Create your models here.
class AuditEvent(models.Model):
    class Action(models.TextChoices):
        REPORT_PRINTED = "report_printed", "Report printed"
        USER_CREATED = "user_created", "Account created"
        USER_UPDATED = "user_updated", "Account edited"
        USER_DEACTIVATED = "user_deactivated", "Account deactivated"
        USER_REACTIVATED = "user_reactivated", "Account reactivated"
        USER_DELETED = "user_deleted", "Account deleted"

    USER_ACTIONS = [
        Action.USER_CREATED, Action.USER_UPDATED, Action.USER_DEACTIVATED,
        Action.USER_REACTIVATED, Action.USER_DELETED,
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=32, choices=Action.choices)
    department = models.CharField(max_length=10, blank=True)   # scoping key (see table above)

    # Who did it: FK for joins, snapshots for permanence
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    actor_username = models.CharField(max_length=150)
    actor_role = models.CharField(max_length=10)
    actor_department = models.CharField(max_length=10, blank=True)

    # Who it was done to (account events only)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    target_username = models.CharField(max_length=150, blank=True)
    target_role = models.CharField(max_length=10, blank=True)

    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["department", "-timestamp"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit events are append-only.")
        super().save(*args, **kwargs)

    def summary(self):
        d = self.detail or {}
        if self.action == self.Action.REPORT_PRINTED:
            text = f"{d.get('report', '?').title()} report"
            if "start_year" in d and "end_year" in d:
                text += f" ({d['start_year']}–{d['end_year']})"
            return text + (f", {d['rows']} rows" if "rows" in d else "")
        if d.get("changes"):
            return "; ".join(
                f"{k}: {v['from'] or '—'} → {v['to'] or '—'}" for k, v in d["changes"].items()
            )
        if self.action == self.Action.USER_CREATED:
            return f"Role: {d.get('role', '')}, department: {d.get('department') or '—'}"
        return ""
