"""
TODO -- views for student support
"""
from edxmako.shortcuts import render_to_response

from support.decorators import require_support_permission


@require_support_permission
def index(request, *args, **kwargs):
    """TODO """
    return render_to_response("support/index.html")
