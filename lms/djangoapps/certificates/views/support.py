"""
Certificate end-points used by the student support UI.

See lms/djangoapps/support for more details.

"""
import logging
from functools import wraps

from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseServerError
)
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from django.utils.translation import ugettext as _

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from student.models import User, CourseEnrollment
from courseware.access import has_access
from util.json_request import JsonResponse
from certificates import api


log = logging.getLogger(__name__)


def require_certificate_permission(func):
    """TODO """
    @wraps(func)
    def inner(request, *args, **kwargs):
        if has_access(request.user, "certificates", "global"):
            return func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    return inner


@require_GET
@require_certificate_permission
def search_by_user(request):
    """TODO """
    query = request.GET.get("query")
    if not query:
        return JsonResponse({})

    try:
        user = User.objects.get(Q(email=query) | Q(username=query))
    except User.DoesNotExist:
        return JsonResponse([])

    certificates = api.get_certificates_for_user(user.username)
    for cert in certificates:
        cert["course_key"] = unicode(cert["course_key"])
        cert["created"] = cert["created"].isoformat()
        cert["modified"] = cert["modified"].isoformat()

    return JsonResponse(certificates)


def _validate_regen_post_params(params):
    """TODO """
    # Validate the username
    try:
        username = params.get("username")
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        msg = _("User {username} does not exist").format(username=username)
        return None, HttpResponseBadRequest(msg)

    # Validate the course key
    try:
        course_key = CourseKey.from_string(params.get("course_key"))
    except InvalidKeyError:
        msg = _("{course_key} is not a valid course key").format(course_key=params.get("course_key"))
        return None, HttpResponseBadRequest(msg)

    return {"user": user, "course_key": course_key}, None


@require_POST
@require_certificate_permission
def regenerate_certificate_for_user(request):
    """TODO """
    params, response = _validate_regen_post_params(request.POST)
    if response is not None:
        return response

    # TODO: really shouldn't need to do this...
    course = modulestore().get_course(params["course_key"])
    if course is None:
        msg = _("The course {course_key} does not exist").format(course_key=params["course_key"])
        return HttpResponseBadRequest(msg)

    if not CourseEnrollment.is_enrolled(params["user"], params["course_key"]):
        msg = _("User {username} is not enrolled in the course {course_key}").format(
            username=params["user"].username,
            course_key=params["course_key"]
        )
        return HttpResponseBadRequest(msg)

    try:
        api.regenerate_user_certificates(params["user"], params["course_key"], course=course)
    except:
        log.exception("Could not regenerate certificates for user %s in course %s", params["user"].id, params["course_key"])
        return HttpResponseServerError(_("An unexpected error occurred while regenerating certificates."))

    log.info(
        "Started regenerating certificates for user %s in course %s from the support page.",
        params["user"].id, params["course_key"]
    )
    return HttpResponse(200)
