from .models import AuditEvent

SENSITIVE_FIELDS = {"password", "password1", "password2"}

def changes_from_form(form):
    """Old -> new values for edited fields. Never includes passwords."""
    return {
        f: {"from": str(form.initial.get(f, "") or ""),
            "to": str(form.cleaned_data.get(f, "") or "")}
        for f in form.changed_data if f not in SENSITIVE_FIELDS
    }


def record(actor, action, *, department="", target=None, detail=None, request=None):
    return AuditEvent.objects.create(
        action=action,
        department=department,
        actor=actor,
        actor_username=actor.get_username(),
        actor_role=actor.role,
        actor_department=actor.department,
        target_user=target,
        target_username=target.get_username() if target else "",
        target_role=target.role if target else "",
        detail=detail or {},
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )

def record_anonymous(action, *, username="", detail=None, request=None):
    """For events where nobody is logged in (failed login)."""
    return AuditEvent.objects.create(
        action=action,
        department="",
        actor=None,
        actor_username=username or "(unknown)",
        actor_role="",
        actor_department="",
        detail=detail or {},
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )