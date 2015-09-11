"""
Command to load course overviews.
"""
import logging
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview


log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Example usage:
        $ ./manage.py lms generate_course_overview --all --settings=devstack
        $ ./manage.py lms generate_course_overview 'edX/DemoX/Demo_Course' --settings=devstack
    """
    args = '<course_id course_id ...>'
    help = 'Generates and stores course overview for one or more courses.'

    option_list = BaseCommand.option_list + (
        make_option('--all',
                    action='store_true',
                    default=False,
                    help='Generate course overview for all courses.'),
    )

    def handle(self, *args, **options):

        if options['all']:
            course_keys = [course.id for course in modulestore().get_courses()]
        else:
            if len(args) < 1:
                raise CommandError('At least one course or --all must be specified.')
            course_keys = [CourseKey.from_string(arg) for arg in args]

        if not course_keys:
            log.fatal('No courses specified.')

        log.info('Generating course overview for %d courses.', len(course_keys))
        log.debug('Generating course overview(s) for the following courses: %s', course_keys)

        for course_key in course_keys:
            try:
                CourseOverview.get_from_id(course_key)
            except Exception as ex:  # pylint: disable=broad-except
                log.exception('An error occurred while generating course overview for %s: %s', unicode(
                    course_key), ex.message)

        log.info('Finished generating course overviews.')
