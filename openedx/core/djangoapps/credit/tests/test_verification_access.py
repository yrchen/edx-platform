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
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory, check_mongo_calls_range


class VerificationAccessRuleTest(ModuleStoreTestCase):
    """
    Tests for applying verification access rules.
    """

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
        # Check that a new partition is created for the verification checkpoint
        course = self._apply_rules()
        self.assertEqual(course.user_partitions, [
            {
                "foo": "bar"
            }
        ])

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

    def _apply_rules(self):
        """TODO """
        apply_verification_access_rules(self.course.id)
        return modulestore().get_course(self.course.id)
