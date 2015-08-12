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
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import ModuleStoreEnum


def apply_verification_access_rules(course_key):
    """
    TODO
    """
    # Retrieve all in-course reverification blocks in the course
    # Hopefully, there won't be any, so we can exit without doing
    # any additional work.
    icrv_blocks, course = _get_icrv_blocks_and_course(course_key)

    if not icrv_blocks:
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


def _get_icrv_blocks_and_course(course):
    pass


def _set_verification_partitions(course, icrv_blocks):
    pass


def _tag_icrv_block_and_exam(icrv_block):
    pass
