"""
Tests for in-course reverification access rules.

This should really belong to the verify_student app,
but we can't move it there because it's in the LMS and we're
currently applying these rules on publish from Studio.

In the future, this functionality should be a course transformation
defined in the verify_student app, and these tests should be moved
into verify_student.

"""

from openedx.core.djangoapps.credit.verification_access import apply_verification_access_rules
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase


class VerificationAccessRuleTest(ModuleStoreTestCase):
    """
    Tests for applying verification access rules.
    """

    def setUp(self):
        super(VerificationAccessRuleTest, self).setUp()

    def test_creates_user_partitions(self):
        self.fail("TODO")

    def test_removes_old_user_partitions(self):
        self.fail("TODO")

    def test_preserves_existing_user_partitions(self):
        self.fail("TODO")

    def test_tags_reverification_block(self):
        self.fail("TODO")

    def test_tags_exam_content(self):
        self.fail("TODO")

    def test_removes_old_tags_from_reverification_block(self):
        self.fail("TODO")

    def test_removes_old_tags_from_exam_content(self):
        self.fail("TODO")

    def test_query_counts_with_no_reverification_blocks(self):
        self.fail("TODO")

    def test_query_counts_with_one_reverification_block(self):
        self.fail("TODO")

    def test_query_counts_with_multiple_reverification_blocks(self):
        self.fail("TODO")
