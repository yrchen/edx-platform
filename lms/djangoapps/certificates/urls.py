"""
URLs for the certificates app.
"""

from django.conf.urls import patterns, url
from django.conf import settings

from certificates import views

urlpatterns = patterns(
    '',

    # Certificates HTML view
    url(
        r'^user/(?P<user_id>[^/]*)/course/{course_id}'.format(course_id=settings.COURSE_ID_PATTERN),
        views.render_html_view,
        name='html_view'
    ),
)


if settings.FEATURES.get("ENABLE_OPENBADGES", False):
    urlpatterns += (
        url(
            r'^badge_share_tracker/{}/(?P<network>[^/]+)/(?P<student_username>[^/]+)/$'.format(settings.COURSE_ID_PATTERN),
            views.track_share_redirect,
            name='badge_share_tracker'
        ),
    )
