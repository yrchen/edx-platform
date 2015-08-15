"""
Partition scheme for in-course reverification.

This is responsible for placing users into one of two groups,
ALLOW or DENY, for a partition associated with a particular
in-course reverification checkpoint.

NOTE: This really should be defined in the verify_student app,
which owns the verification and reverification process.
It isn't defined there now because (a) we need access to this in both Studio
and the LMS, but verify_student is specific to the LMS, and
(b) in-course reverification checkpoints currently have messaging that's
specific to credit requirements.

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

        # Decide whether the user should have access to content gated by this checkpoint.
        # Intuitively, we allow access if the user doesn't need to do anything at the checkpoint,
        # either because the user is in a non-verified track or the user has already submitted.
        #
        # Note that we do NOT wait the user's reverification attempt to be approved,
        # since this can take some time and the user might miss an assignment deadline.
        if not is_enrolled_in_verified_mode(user, course_key):
            partition_group = cls.ALLOW
        elif has_skipped_any_checkpoint(user, course_key):
            partition_group = cls.ALLOW
        elif has_completed_checkpoint(user, course_key, checkpoint):
            partition_group = cls.ALLOW
        else:
            partition_group = cls.DENY

        # Return matching user partition group if it exists
        try:
            return user_partition.get_group(partition_group)
        except NoSuchUserPartitionGroupError:
            log.error(
                (
                    u"Could not find group with ID %s for verified partition "
                    "with ID %s in course %s.  The user will not be assigned a group."
                ),
                partition_group,
                user_partition.id,
                course_key
            )
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
