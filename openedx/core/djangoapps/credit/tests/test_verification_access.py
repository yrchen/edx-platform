"""
Tests for in-course reverification access rules.

This should really belong to the verify_student app,
but we can't move it there because it's in the LMS and we're
currently applying these rules on publish from Studio.

In the future, this functionality should be a course transformation
defined in the verify_student app, and these tests should be moved
into verify_student.

"""

from mock import patch

from django.conf import settings

from openedx.core.djangoapps.credit.models import CreditCourse
from openedx.core.djangoapps.credit.partition_schemes import VerificationPartitionScheme
from openedx.core.djangoapps.credit.verification_access import apply_verification_access_rules
from openedx.core.djangoapps.credit.signals import on_pre_publish
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import SignalHandler
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase, TEST_DATA_SPLIT_MODULESTORE
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory, check_mongo_calls_range
from xmodule.partitions.partitions import Group, UserPartition


class VerificationAccessRuleTest(ModuleStoreTestCase):
    """
    Tests for applying verification access rules.
    """

    # TODO: explain this
    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    @patch.dict(settings.FEATURES, {"ENABLE_COURSEWARE_INDEX": False})
    def setUp(self):
        super(VerificationAccessRuleTest, self).setUp()

        # Disconnect the signal receiver -- we'll invoke the update code ourselves
        SignalHandler.pre_publish.disconnect(receiver=on_pre_publish)
        self.addCleanup(SignalHandler.pre_publish.connect, receiver=on_pre_publish)

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

    @patch.dict(settings.FEATURES, {"ENABLE_COURSEWARE_INDEX": False})
    def test_removes_deleted_user_partitions(self):
        # Apply the rules to create the user partition for the checkpoint
        self._apply_rules()

        # Delete the reverification block, then update the access rules
        self.store.delete_item(
            self.icrv.location,
            ModuleStoreEnum.UserID.test,
            revision=ModuleStoreEnum.RevisionOption.published_only,
        )
        self._apply_rules()

        # Check that the user partition was removed from the course
        self.assertEqual(self.course.user_partitions, [])

    @patch.dict(settings.FEATURES, {"ENABLE_COURSEWARE_INDEX": False})
    def test_preserves_existing_user_partitions(self):
        # Add other, non-verified partition to the course
        self.course.user_partitions = [
            UserPartition(
                id=0,
                name='Cohort user partition',
                scheme=UserPartition.get_scheme('cohort'),
                description='Cohorted user partition',
                groups=[
                    Group(id=0, name="Group A"),
                    Group(id=1, name="Group B"),
                ],
            ),
            UserPartition(
                id=1,
                name='Random user partition',
                scheme=UserPartition.get_scheme('random'),
                description='Random user partition',
                groups=[
                    Group(id=0, name="Group A"),
                    Group(id=1, name="Group B"),
                ],
            ),
        ]
        self.course = self.store.update_item(self.course, ModuleStoreEnum.UserID.test)

        # Apply the verification rules.
        # The existing partitions should still be available
        self._apply_rules()
        partition_ids = [p.id for p in self.course.user_partitions]
        self.assertEqual(len(partition_ids), 3)
        self.assertIn(0, partition_ids)
        self.assertIn(1, partition_ids)

    @patch.dict(settings.FEATURES, {"ENABLE_COURSEWARE_INDEX": False})
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

    @patch.dict(settings.FEATURES, {"ENABLE_COURSEWARE_INDEX": False})
    def test_tags_exam_content(self):
        self._apply_rules()

        # Check that the correct "exam" content has been tagged
        partition_id = self.course.user_partitions[0].id
        for block in self.exam_content:
            self.assertIn(partition_id, block.group_access)
            groups = block.group_access[partition_id]
            self.assertItemsEqual(
                groups,
                [
                    VerificationPartitionScheme.NON_VERIFIED,
                    VerificationPartitionScheme.VERIFIED_ALLOW,
                ]
            )

        # Check that non-exam content has NOT been tagged.
        for block in self.non_exam_content:
            self.assertEqual(
                block.group_access, {},
                msg="Expected block {} to not be tagged".format(block.display_name)
            )

    def test_preserves_existing_tags_in_exam_content(self):
        self._apply_rules()
        self.fail("TODO")

    def test_removes_deleted_tags_from_reverification_block(self):
        self._apply_rules()
        self.fail("TODO")

    def test_removes_deleted_tags_from_exam_content(self):
        self.fail("TODO")

    def test_applying_rules_preserves_has_changes(self):
        # Since we haven't changed the draft since publishing,
        # applying the rules should not introduce any changes
        self.assertFalse(self.store.has_changes(self.icrv))
        self._apply_rules()
        self.assertFalse(self.store.has_changes(self.icrv))

        # Update the ICRV block's draft version, then apply access rules
        self.icrv.display_name = "Foobar"
        self.store.update_item(self.icrv, ModuleStoreEnum.UserID.test)

        # Expect that changes are preserved
        self.assertTrue(self.store.has_changes(self.icrv))
        self._apply_rules()
        self.assertTrue(self.store.has_changes(self.icrv))

        # TODO -- expect that the draft version still says "Foobar"

    def test_multiple_reverification_blocks(self):
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
            self.sections = [self._reload_item(section.location) for section in self.sections]
            self.subsections = [self._reload_item(subsection.location) for subsection in self.subsections]
            self.verticals = [self._reload_item(vertical.location) for vertical in self.verticals]
            self.icrv = self._reload_item(self.icrv.location)
            self.sibling_problem = self._reload_item(self.sibling_problem.location)

    def _reload_item(self, location):
        """TODO """
        try:
            return self.store.get_item(location)
        except ItemNotFoundError:
            return None

    @property
    def exam_content(self):
        """TODO """
        # "Exam" content doesn't really exist in the course tree, except as assessment
        # content within a sequential.  We use some simple heuristics to tag this content.
        return [

            # The sibling vertical is included,
            # but not the parent vertical, since access rules are inherited and
            # we need to see the ICRV block.
            self.verticals[1],

            # The sibling assessment within the ICRV's vertical
            self.sibling_problem,
        ]

    @property
    def non_exam_content(self):
        """TODO """
        return [
            self.sections[0], self.sections[1],
            self.subsections[0], self.subsections[1], self.subsections[2], self.subsections[3],
            self.verticals[0], self.verticals[2], self.verticals[3], self.verticals[4],
            self.verticals[5], self.verticals[6], self.verticals[7],
        ]


class WriteOnPublishTest(ModuleStoreTestCase):
    """
    Verify that changes are written automatically on publish.
    """
    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    @patch.dict(settings.FEATURES, {"ENABLE_COURSEWARE_INDEX": False})
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

    @patch.dict(settings.FEATURES, {"ENABLE_COURSEWARE_INDEX": False})
    def test_can_write_on_publish_signal(self):
        # Sanity check -- initially user partitions should be empty
        self.assertEqual(self.course.user_partitions, [])
        self.assertEqual(self.icrv.group_access, {})

        # Make and publish a change to a block, which should trigger the publish signal
        with self.store.bulk_operations(self.course.id):
            self.icrv.display_name = "Updated display name"
            self.store.update_item(self.icrv, ModuleStoreEnum.UserID.test)
            self.store.publish(self.icrv.location, ModuleStoreEnum.UserID.test)

        # Within the test, the course pre-publish signal should have fired synchronously
        # Since the course is marked as credit, the in-course verification access
        # rules should have been applied.
        # We need to verify that these changes were actually persisted to the modulestore.
        with self.store.branch_setting(ModuleStoreEnum.Branch.published_only):
            retrieved_course = self.store.get_course(self.course.id)
            self.assertEqual(len(retrieved_course.user_partitions), 1)
            retrieved_icrv = self.store.get_item(self.icrv.location)
            self.assertEqual(len(retrieved_icrv.group_access), 1)
