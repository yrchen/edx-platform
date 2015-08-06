"""
Index view for the support app.
"""
from edxmako.shortcuts import render_to_response
from support.decorators import require_support_permission


@require_support_permission
def index(request):  # pylint: disable=unused-argument
    """Render the support index view. """
    return render_to_response("support/index.html")
