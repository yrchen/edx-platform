"""
Tests for in-course reverification access rules.

This should really belong to the verify_student app,
but we can't move it there because it's in the LMS and we're
currently applying these rules on publish from Studio.

In the future, this functionality should be a course transformation
defined in the verify_student app, and these tests should be moved
into verify_student.

"""

from openedx.core.djangoapps.credit.models import CreditCourse
from openedx.core.djangoapps.credit.partition_schemes import VerificationPartitionScheme
from openedx.core.djangoapps.credit.verification_access import apply_verification_access_rules
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase, TEST_DATA_SPLIT_MODULESTORE
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory, check_mongo_calls_range


class VerificationAccessRuleTest(ModuleStoreTestCase):
    """
    Tests for applying verification access rules.
    """

    # TODO: explain this
    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    def setUp(self):
        super(VerificationAccessRuleTest, self).setUp()

        # Create a dummy course with a single verification checkpoint
        # Because we need to check "exam" content surrounding the ICRV checkpoint,
        # we need to create a fairly large course structure, with multiple sections,
        # subsections, verticals, units, and items.
        self.course = CourseFactory()
        self.sections = [
            ItemFactory.create(parent=self.course, category='chapter', display_name='Test Section A'),
            ItemFactory.create(parent=self.course, category='chapter', display_name='Test Section B'),
        ]
        self.subsections = [
            ItemFactory.create(parent=self.sections[0], category='sequential', display_name='Test Subsection A 1'),
            ItemFactory.create(parent=self.sections[0], category='sequential', display_name='Test Subsection A 2'),
            ItemFactory.create(parent=self.sections[1], category='sequential', display_name='Test Subsection B 1'),
            ItemFactory.create(parent=self.sections[1], category='sequential', display_name='Test Subsection B 2'),
        ]
        self.verticals = [
            ItemFactory.create(parent=self.subsections[0], category='vertical', display_name='Test Unit A 1 a'),
            ItemFactory.create(parent=self.subsections[0], category='vertical', display_name='Test Unit A 1 b'),
            ItemFactory.create(parent=self.subsections[1], category='vertical', display_name='Test Unit A 2 a'),
            ItemFactory.create(parent=self.subsections[1], category='vertical', display_name='Test Unit A 2 b'),
            ItemFactory.create(parent=self.subsections[2], category='vertical', display_name='Test Unit B 1 a'),
            ItemFactory.create(parent=self.subsections[2], category='vertical', display_name='Test Unit B 1 b'),
            ItemFactory.create(parent=self.subsections[3], category='vertical', display_name='Test Unit B 2 a'),
            ItemFactory.create(parent=self.subsections[3], category='vertical', display_name='Test Unit B 2 b'),
        ]

        self.icrv = ItemFactory.create(parent=self.verticals[0], category='edx-reverification-block')
        self.sibling_problem = ItemFactory.create(parent=self.verticals[0], category='problem')

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


class WriteOnPublishTest(ModuleStoreTestCase):
    """
    TODO -- explain why this test is necessary.
    """
    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    def setUp(self):
        super(WriteOnPublishTest, self).setUp()

        # Create a dummy course with an ICRV block
        self.course = CourseFactory()
        self.section = ItemFactory.create(parent=self.course, category='chapter', display_name='Test Section')
        self.subsection = ItemFactory.create(parent=self.section, category='sequential', display_name='Test Subsection')
        self.vertical = ItemFactory.create(parent=self.subsection, category='vertical', display_name='Test Unit')
        self.icrv = ItemFactory.create(parent=self.vertical, category='edx-reverification-block')

        # Mark the course as credit
        CreditCourse.objects.create(course_key=self.course.id, enabled=True)

    def test_can_write_on_publish_signal(self):
        # Sanity check -- initially user partitions should be empty
        self.assertEqual(self.course.user_partitions, [])

        # Make and publish a change to a block, which should trigger the publish signal
        with self.store.bulk_operations(self.course.id):
            self.icrv.display_name = "Updated display name"
            self.store.update_item(self.icrv, ModuleStoreEnum.UserID.test)
            self.store.publish(self.icrv.location, ModuleStoreEnum.UserID.test)

        # Within the test, the course publish signal should have fired synchronously
        # Since the course is marked as credit, the in-course verification access
        # rules should have been applied.
        # We need to verify that these changes were actually persisted to the modulestore.
        retrieved_course = self.store.get_course(self.course.id)
        self.assertEqual(len(retrieved_course.user_partitions), 1)
