from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def instrutor_required(view):
    @login_required
    @wraps(view)
    def verificar(request, *args, **kwargs):
        if not request.user.pode_instruir:
            raise PermissionDenied('Esta área é exclusiva para instrutores.')
        return view(request, *args, **kwargs)
    return verificar
