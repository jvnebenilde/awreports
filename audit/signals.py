from django.contrib.auth.signals import (
    user_logged_in, user_logged_out, user_login_failed,
)
from django.dispatch import receiver
from .models import AuditEvent
from .services import record, record_anonymous

A = AuditEvent.Action


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    record(user, A.LOGIN, department=user.department, request=request)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:
        record(user, A.LOGOUT, department=user.department, request=request)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    record_anonymous(A.LOGIN_FAILED,
                     username=credentials.get("username", ""), request=request)