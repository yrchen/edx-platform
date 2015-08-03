"""
TODO -- views for student support
"""
from functools import wraps

from django.http import HttpResponseForbidden

from edxmako.shortcuts import render_to_response
from courseware.access import has_access


def require_support_permission(func):
    """TODO """
    @wraps(func)
    def inner(request, *args, **kwargs):
        if has_access(request.user, "support", "global"):
            return func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    return inner


@require_support_permission
def index(request, *args, **kwargs):
    """TODO """
    return render_to_response("support/index.html")
