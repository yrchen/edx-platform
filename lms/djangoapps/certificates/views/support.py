"""
Certificate end-points used by the student support UI.

See lms/djangoapps/support for more details.

"""
from functools import wraps

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_GET, require_POST

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from student.models import User, CourseEnrollment
from courseware.access import has_access
from util.json_request import JsonResponse
from certificates import api


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
def get_user_certificates(request, username=None):
    """TODO """
    certificates = api.get_certificates_for_user(username)
    for cert in certificates:
        cert["course_key"] = unicode(cert["course_key"])

    return JsonResponse(certificates)


def _validate_regen_post_params(params):
    """TODO """
    # Validate the username
    try:
        username = params.get("username")
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return None, HttpResponseBadRequest("User does not exist")

    # Validate the course key
    try:
        course_key = CourseKey.from_string(params.get("course_key"))
    except InvalidKeyError:
        return None, HttpResponseBadRequest("Invalid course key")

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
        return HttpResponseBadRequest("The course does not exist")

    if not CourseEnrollment.is_enrolled(params["user"], params["course_key"]):
        return HttpResponseBadRequest("The user is not enrolled in the course")

    status = api.regenerate_user_certificates(params["user"], params["course_key"], course=course)

    return HttpResponse(200)
