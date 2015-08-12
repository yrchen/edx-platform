"""
Tests for in-course reverification access rules.

This should really belong to the verify_student app,
but we can't move it there because it's in the LMS and we're
currently applying these rules on publish from Studio.

In the future, this functionality should be a course transformation
defined in the verify_student app, and these tests should be moved
into verify_student.

"""

from openedx.core.djangoapps.credit.partition_schemes import VerificationPartitionScheme
from openedx.core.djangoapps.credit.verification_access import apply_verification_access_rules
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.utils import MixedSplitTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory, check_mongo_calls_range


class VerificationAccessRuleTest(MixedSplitTestCase):
    """
    Tests for applying verification access rules.
    """

    def setUp(self):
        super(VerificationAccessRuleTest, self).setUp()

        # Create a dummy course with a single verification checkpoint
        # Because we need to check "exam" content surrounding the ICRV checkpoint,
        # we need to create a fairly large course structure, with multiple sections,
        # subsections, verticals, units, and items.
        self.course = CourseFactory(modulestore=self.store)
        self.sections = [
            self.make_block("chapter", self.course, display_name="Test Section A"),
            self.make_block("chapter", self.course, display_name="Test Section B"),
        ]
        self.subsections = [
            self.make_block("sequential", self.sections[0], display_name="Test Subsection A 1"),
            self.make_block("sequential", self.sections[0], display_name="Test Subsection A 2"),
            self.make_block("sequential", self.sections[1], display_name="Test Subsection B 1"),
            self.make_block("sequential", self.sections[1], display_name="Test Subsection B 2"),
        ]
        self.verticals = [
            self.make_block("vertical", self.subsections[0], display_name="Test Unit A 1 a"),
            self.make_block("vertical", self.subsections[0], display_name="Test Unit A 1 b"),
            self.make_block("vertical", self.subsections[1], display_name="Test Unit A 2 a"),
            self.make_block("vertical", self.subsections[1], display_name="Test Unit A 2 b"),
            self.make_block("vertical", self.subsections[2], display_name="Test Unit B 1 a"),
            self.make_block("vertical", self.subsections[2], display_name="Test Unit B 1 b"),
            self.make_block("vertical", self.subsections[3], display_name="Test Unit B 2 a "),
            self.make_block("vertical", self.subsections[3], display_name="Test Unit B 2 b"),
        ]

        self.icrv = self.make_block("edx-reverification-block", self.verticals[0])
        self.sibling_problem = self.make_block("problem", self.verticals[0])

    def test_creates_user_partitions(self):
        # Transform the course by applying ICRV access rules
        self._apply_rules()

        # Check that a new user partition was created for the ICRV block
        self.assertEqual(len(self.course.user_partitions), 1)
        partition = self.course.user_partitions[0]
        self.assertEqual(partition.scheme.name, "verification")
        self.assertEqual(partition.parameters["location"], unicode(self.icrv.location))

        # Check that the groups for the partition were created correctly
        self.assertEqual(len(partition.groups), 3)
        self.assertItemsEqual(
            [g.id for g in partition.groups],
            [
                VerificationPartitionScheme.NON_VERIFIED,
                VerificationPartitionScheme.VERIFIED_DENY,
                VerificationPartitionScheme.VERIFIED_ALLOW
            ]
        )

    def test_removes_old_user_partitions(self):
        self.fail("TODO")

    def test_preserves_existing_user_partitions(self):
        self.fail("TODO")

    def test_tags_reverification_block(self):
        self._apply_rules()

        # Check that the ICRV block's allowed groups have been updated
        self.assertEqual(len(self.course.user_partitions), 1)
        partition_id = self.course.user_partitions[0].id
        self.assertIn(partition_id, self.icrv.group_access)

        # Expect that verified deny and verified allow groups are set
        # so that users who are verified can see the block.
        groups = self.icrv.group_access[partition_id]
        self.assertItemsEqual(
            groups,
            [
                VerificationPartitionScheme.VERIFIED_DENY,
                VerificationPartitionScheme.VERIFIED_ALLOW
            ]
        )

    def test_tags_exam_content(self):
        self.fail("TODO")

    def test_removes_old_tags_from_reverification_block(self):
        self.fail("TODO")

    def test_removes_old_tags_from_exam_content(self):
        self.fail("TODO")

    def test_applying_rules_preserves_has_changes(self):
        self.fail("TODO")

    def test_applying_rules_does_not_introduce_changes(self):
        self.fail("TODO")

    def test_query_counts_with_no_reverification_blocks(self):
        self.fail("TODO")

    def test_query_counts_with_one_reverification_block(self):
        self.fail("TODO")

    def test_query_counts_with_multiple_reverification_blocks(self):
        self.fail("TODO")

    def _apply_rules(self):
        """TODO """
        apply_verification_access_rules(self.course.id)

        # Reload the published version of each component to get changes
        with self.store.branch_setting(ModuleStoreEnum.Branch.published_only):
            self.course = self.store.get_course(self.course.id)
            self.sections = [self.store.get_item(section.location) for section in self.sections]
            self.subsections = [self.store.get_item(subsection.location) for subsection in self.subsections]
            self.verticals = [self.store.get_item(vertical.location) for vertical in self.verticals]
            self.icrv = self.store.get_item(self.icrv.location)
            self.sibling_problem = self.store.get_item(self.sibling_problem.location)
