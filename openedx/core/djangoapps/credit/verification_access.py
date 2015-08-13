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
    icrv_blocks = get_course_blocks(course_key, VERIFICATION_BLOCK_CATEGORY)

    # Batch all the write queries we're about to do and suppress
    # the "publish" signal to avoid an infinite call loop.
    with modulestore().bulk_operations(course_key, emit_signals=False):

        # Update the verification definitions in the course descriptor
        # This will also clean out old verification partitions if checkpoints
        # have been deleted.
        partitions = _set_verification_partitions(course_key, icrv_blocks)

        # Index partitions by their associated reverification block location
        partitions_by_loc = {
            p.parameters["location"]: p
            for p in partitions
        }

        # Update the allowed partition groups for the in-course-reverification block
        # and its surrounding exam content.
        for block in icrv_blocks:
            _tag_icrv_block_and_exam(block, partitions_by_loc)


def _unique_partition_id(course):
    """TODO """
    used_ids = set(p.id for p in course.user_partitions)
    return generate_int_id(used_ids=used_ids)


def _find_other_partitions(course, scheme):
    """TODO """
    return [
        p for p in course.user_partitions
        if p.scheme != scheme
    ]


def _get_exam_blocks(icrv_block):
    """TODO """
    # Sibling assessments of the parent vertical
    # TODO

    # Sibling verticals of the grandparent sequential
    return []


def _set_verification_partitions(course_key, icrv_blocks):
    """TODO """
    scheme = UserPartition.get_scheme(VERIFICATION_SCHEME_NAME)
    if scheme is None:
        # TODO -- log an error here
        return []

    course = modulestore().get_course(course_key)
    if course is None:
        # TODO: log an error here
        return []

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

    # Preserve existing, non-verified partitions from the course
    course.user_partitions = partitions + _find_other_partitions(course, scheme)
    _update_published_item(course)

    return partitions


def _tag_icrv_block_and_exam(icrv_block, partitions_by_loc):
    """TODO """

    # Set the groups for the reverification block
    # TODO: play nicely with existing groups
    partition = partitions_by_loc.get(unicode(icrv_block.location))
    if partition is None:
        # This should never happen, but be defensive
        # TODO log
        return

    # Update the in-course reverification block itself
    # TODO: explain why these two groups are used
    icrv_block.group_access = {
        partition.id: [
            partition.scheme.VERIFIED_ALLOW,
            partition.scheme.VERIFIED_DENY,
        ]
    }
    _update_published_item(icrv_block)

    # Update the exam content associated with the reverification block
    # TODO: lots of explanation here
    for block in _get_exam_blocks(icrv_block):
        block.group_access = {
            partition.id: [
                partition.scheme.NON_VERIFIED,
                partition.scheme.VERIFIED_ALLOW,
            ]
        }
        _update_published_item(block)


def _update_published_item(item):
    store = modulestore()
    with store.branch_setting(ModuleStoreEnum.Branch.published_only, course_id=item.location.course_key):
        result = store.update_item(item, ModuleStoreEnum.UserID.system)
