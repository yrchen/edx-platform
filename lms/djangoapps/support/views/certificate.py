"""
TODO
"""
from django.http import HttpResponse
from django.views.generic import View
from django.utils.decorators import method_decorator

from edxmako.shortcuts import render_to_response
from support.decorators import require_support_permission


class CertificatesSupportView(View):
    """TODO"""

    @method_decorator(require_support_permission)
    def get(self, request):
        context = {
            "user_query": request.GET.get("query", "")
        }
        return render_to_response("support/certificates.html", context)

    @method_decorator(require_support_permission)
    def post(self, request):
        return HttpResponse("POST CERTIFICATES!")
