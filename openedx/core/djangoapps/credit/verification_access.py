"""
Apply in-course reverification access rules to a course.

We model the rules as a set of user partitions, one for each
verification checkpoint in a course.

For example, suppose that a course has two verification checkpoints,
one at midterm A and one at the midterm B.

Then the user partitions would look like this:

Midterm A:  |-- NON_VERIFIED --|-- VERIFIED_DENY --|-- VERIFIED_ALLOW --|
Midterm B:  |-- NON_VERIFIED --|-- VERIFIED_DENY --|-- VERIFIED_ALLOW --|

where the groups are defined as:

* NON_VERIFIED: The user is not in a verified track, so the user sees exam
   content, but not the verification checkpoint block.

* VERIFIED_DENY: The user is in a verified track, but has not yet submitted
   photos at the checkpoint.  The user can see the verification checkpoint block,
   but not the exam content.

* VERIFIED_ALLOW: The user is in a verfied track and has submitted photos
   at the checkpoint.  The user can see both the verification checkpoint block
   (which shows status messaging of the verification attempt) as well as the exam content.

The code that puts users into particular groups based on their verification and enrollment
status is a user partition scheme defined in the verify_student app.  This is just a function
mapping users to the above groups for each verification-related partition in the course.

The tricky thing is that we need to update the course structure to:
(a) define partitions for each verification checkpoint
(b) tag the allowed groups for each verification checkpoint block
(c) tag the allowed groups for exam content associated with a verification checkpoint block.

Once the content is tagged with the appropriate groups, the LMS can use
the partition scheme function to put users into groups and check access.

Ideally, this would be a transformation of the course structure run as a pre-processing
step by the LMS.  Unfortunately, that infrastructure does not yet exist, so currently we're
modifying the course automatically on publish from Studio.

"""
from util.db import generate_int_id
from openedx.core.djangoapps.credit.utils import get_course_blocks
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import ModuleStoreEnum
from xmodule.partitions.partitions import Group, UserPartition, NoSuchUserPartitionError


VERIFICATION_SCHEME_NAME = "verification"
VERIFICATION_BLOCK_CATEGORY = "edx-reverification-block"


def apply_verification_access_rules(course_key):
    """
    TODO
    """
    # Retrieve all in-course reverification blocks in the course
    # Hopefully, there won't be any, so we can exit without doing
    # any additional work.
    icrv_blocks = get_course_blocks(course_key, VERIFICATION_BLOCK_CATEGORY)

    if not icrv_blocks:
        return

    course = modulestore().get_course(course_key)
    if course is None:
        # TODO: log an error here
        return

    # Batch all the write queries we're about to do and suppress
    # the "publish" signal to avoid an infinite call loop.
    with modulestore().bulk_operations(course_key, emit_signals=False):

        # Update the verification definitions in the course descriptor
        # This will also clean out old verification partitions if checkpoints
        # have been deleted.
        _set_verification_partitions(course, icrv_blocks)

        # Update the allowed partition groups for the in-course-reverification block
        # and its surrounding exam content.
        for block in icrv_blocks:
            _tag_icrv_block_and_exam(block)


def _unique_partition_id(course):
    used_ids = set(p.id for p in course.user_partitions)
    return generate_int_id(used_ids=used_ids)


def _set_verification_partitions(course, icrv_blocks):

    scheme = UserPartition.get_scheme(VERIFICATION_SCHEME_NAME)
    if scheme is None:
        # TODO -- log an error here
        return

    partitions = [
        UserPartition(
            id=_unique_partition_id(course),
            name=u"Verification Checkpoint",
            description=u"Verification Checkpoint",  # TODO: add anything else here?
            scheme=scheme,
            parameters={"location": unicode(block.location)},
            groups=[
                Group(scheme.NON_VERIFIED, "Not enrolled in a verified track"),
                Group(scheme.VERIFIED_ALLOW, "Enrolled in a verified track and has access to exam content"),
                Group(scheme.VERIFIED_DENY, "Enrolled in a verified track and does not have access to exam content"),
            ]
        )
        for block in icrv_blocks
    ]

    course.user_partitions = partitions
    modulestore().update_item(course, ModuleStoreEnum.UserID.system)


def _tag_icrv_block_and_exam(icrv_block):
    pass
