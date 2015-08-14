"""
TODO: fix this docstring!
"""

import logging

from course_modes.models import CourseMode
from lms.djangoapps.verify_student.models import SkippedReverification, VerificationStatus
from student.models import CourseEnrollment
from xmodule.partitions.partitions import NoSuchUserPartitionGroupError


log = logging.getLogger(__name__)


class VerificationPartitionScheme(object):
    """
    This scheme assigns users into the partition 'VerificationPartitionScheme'
    groups. Initially all the gated exams content will be hidden except the
    ICRV blocks for a 'verified' student until that student skips or submits
    verification for an ICRV then the related gated exam content for that ICRV
    will be displayed.

    """
    DENY = 0
    ALLOW = 1

    @classmethod
    def get_group_for_user(cls, course_key, user, user_partition):
        """
        Return the user's group depending their enrollment and verification
        status.

        Args:
            course_key(CourseKey): CourseKey
            user(User): user object
            user_partition: location object

        Returns:
            string of allowed access group
        """
        checkpoint = user_partition.parameters['location']
        if (
            not is_enrolled_in_verified_mode(user, course_key) or
            has_skipped_any_checkpoint(user, course_key) or
            has_completed_checkpoint(user, course_key, checkpoint)
        ):
            # the course content tagged with given 'user_partition' is
            # accessible/visible to the students enrolled as `verified` users
            # and has either `skipped any ICRV` or `was denied at any ICRV
            # (used all attempts for an ICRV but still denied by the software
            # secure)` or `has submitted/approved verification for given ICRV`
            partition_group = cls.ALLOW
        else:
            # the course content tagged with given 'user_partition' is
            # accessible/visible to the students enrolled as `verified` users
            # and has not yet submitted for the related ICRV
            partition_group = cls.DENY

        # return matching user partition group if it exists
        try:
            return user_partition.get_group(partition_group)
        except NoSuchUserPartitionGroupError:
            # TODO -- log here
            return None


def is_enrolled_in_verified_mode(user, course_key):
    """
    Returns the Boolean value if given user for the given course is enrolled in
    verified modes.

    Args:
        user(User): user object
        course_key(CourseKey): CourseKey

    Returns:
        Boolean
    """
    enrollment_mode, __ = CourseEnrollment.enrollment_mode_for_user(user, course_key)
    return enrollment_mode in CourseMode.VERIFIED_MODES


def has_skipped_any_checkpoint(user, course_key):
    """Check existence of a user's skipped re-verification attempt for a
    specific course.

    Args:
        user(User): user object
        course_key(CourseKey): CourseKey

    Returns:
        Boolean
    """
    return SkippedReverification.check_user_skipped_reverification_exists(user, course_key)


def has_completed_checkpoint(user, course_key, checkpoint):
    """
    Get re-verification status against a user for a 'course_id' and checkpoint.
    Only 'approved' and 'submitted' statuses are considered as completed.

    Args:
        user (User): The user whose status we are retrieving.
        course_key (CourseKey): The identifier for the course.
        checkpoint (UsageKey): The location of the checkpoint in the course.

    Returns:
        unicode or None
    """
    return VerificationStatus.check_user_has_submitted(user, course_key, checkpoint)
