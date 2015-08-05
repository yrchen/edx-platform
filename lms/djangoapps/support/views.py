"""
TODO -- views for student support
"""
from functools import wraps

from django.http import HttpResponse, HttpResponseForbidden
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

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

    return login_required(inner)


@require_support_permission
def index(request, *args, **kwargs):
    """TODO """
    return render_to_response("support/index.html")


class CertificatesSupportView(View):
    """TODO"""

    @method_decorator(require_support_permission)
    def get(self, request):
        context = {
            "user_query": request.GET.get("query")
        }
        return render_to_response("support/certificates.html", context)

    @method_decorator(require_support_permission)
    def post(self, request):
        return HttpResponse("POST CERTIFICATES!")
