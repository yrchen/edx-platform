"""
TODO
"""
from functools import wraps

from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required

from courseware.access import has_access


def require_support_permission(func):
    """TODO """
    @wraps(func)
    def inner(request, *args, **kwargs):
        if has_access(request.user, "support", "global"):
            return func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    return login_required(inner)
