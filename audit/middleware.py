from .models import AuditEvent
from .services import record


class AccessDeniedAuditMiddleware:
    """Writes an audit entry whenever a signed-in user receives a 403."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if response.status_code == 403 and user is not None and user.is_authenticated:
            record(user, AuditEvent.Action.ACCESS_DENIED,
                   department=user.department,
                   detail={"path": request.path, "method": request.method},
                   request=request)
        return response