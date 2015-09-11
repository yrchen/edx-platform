# -*- coding: utf-8 -*-
"""
Miscellaneous tests for the student app.
"""
from datetime import datetime, timedelta
import logging
import pytz
import unittest
import ddt

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from mock import Mock, patch
from opaque_keys.edx.locations import SlashSeparatedCourseKey

from student.models import (
    anonymous_id_for_user, user_by_anonymous_id, CourseEnrollment, unique_id_for_user, LinkedInAddToProfileConfiguration
)
from student.views import (
    process_survey_link,
    _cert_info,
    complete_course_mode_info,
)
from student.tests.factories import UserFactory, CourseModeFactory
from util.testing import EventTestMixin
from util.model_utils import USER_SETTINGS_CHANGED_EVENT_NAME
from xmodule.modulestore.tests.factories import CourseFactory, check_mongo_calls
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase, ModuleStoreEnum

# These imports refer to lms djangoapps.
# Their testcases are only run under lms.
from bulk_email.models import Optout  # pylint: disable=import-error
from certificates.models import CertificateStatuses  # pylint: disable=import-error
from certificates.tests.factories import GeneratedCertificateFactory  # pylint: disable=import-error
from verify_student.models import SoftwareSecurePhotoVerification
import shoppingcart  # pylint: disable=import-error

# Explicitly import the cache from ConfigurationModel so we can reset it after each test
from config_models.models import cache

log = logging.getLogger(__name__)


@ddt.ddt
class CourseEndingTest(TestCase):
    """Test things related to course endings: certificates, surveys, etc"""

    def test_process_survey_link(self):
        username = "fred"
        user = Mock(username=username)
        user_id = unique_id_for_user(user)
        link1 = "http://www.mysurvey.com"
        self.assertEqual(process_survey_link(link1, user), link1)

        link2 = "http://www.mysurvey.com?unique={UNIQUE_ID}"
        link2_expected = "http://www.mysurvey.com?unique={UNIQUE_ID}".format(UNIQUE_ID=user_id)
        self.assertEqual(process_survey_link(link2, user), link2_expected)

    @patch.dict('django.conf.settings.FEATURES', {'CERTIFICATES_HTML_VIEW': False})
    def test_cert_info(self):
        user = Mock(username="fred")
        survey_url = "http://a_survey.com"
        course = Mock(end_of_course_survey_url=survey_url, certificates_display_behavior='end')
        course_mode = 'honor'

        self.assertEqual(
            _cert_info(user, course, None, course_mode),
            {
                'status': 'processing',
                'show_disabled_download_button': False,
                'show_download_url': False,
                'show_survey_button': False,
            }
        )

        cert_status = {'status': 'unavailable'}
        self.assertEqual(
            _cert_info(user, course, cert_status, course_mode),
            {
                'status': 'processing',
                'show_disabled_download_button': False,
                'show_download_url': False,
                'show_survey_button': False,
                'mode': None,
                'linked_in_url': None
            }
        )

        cert_status = {'status': 'generating', 'grade': '67', 'mode': 'honor'}
        self.assertEqual(
            _cert_info(user, course, cert_status, course_mode),
            {
                'status': 'generating',
                'show_disabled_download_button': True,
                'show_download_url': False,
                'show_survey_button': True,
                'survey_url': survey_url,
                'grade': '67',
                'mode': 'honor',
                'linked_in_url': None
            }
        )

        cert_status = {'status': 'regenerating', 'grade': '67', 'mode': 'verified'}
        self.assertEqual(
            _cert_info(user, course, cert_status, course_mode),
            {
                'status': 'generating',
                'show_disabled_download_button': True,
                'show_download_url': False,
                'show_survey_button': True,
                'survey_url': survey_url,
                'grade': '67',
                'mode': 'verified',
                'linked_in_url': None
            }
        )

        download_url = 'http://s3.edx/cert'
        cert_status = {
            'status': 'downloadable', 'grade': '67',
            'download_url': download_url,
            'mode': 'honor'
        }

        self.assertEqual(
            _cert_info(user, course, cert_status, course_mode),
            {
                'status': 'ready',
                'show_disabled_download_button': False,
                'show_download_url': True,
                'download_url': download_url,
                'show_survey_button': True,
                'survey_url': survey_url,
                'grade': '67',
                'mode': 'honor',
                'linked_in_url': None
            }
        )

        cert_status = {
            'status': 'notpassing', 'grade': '67',
            'download_url': download_url,
            'mode': 'honor'
        }
        self.assertEqual(
            _cert_info(user, course, cert_status, course_mode),
            {
                'status': 'notpassing',
                'show_disabled_download_button': False,
                'show_download_url': False,
                'show_survey_button': True,
                'survey_url': survey_url,
                'grade': '67',
                'mode': 'honor',
                'linked_in_url': None
            }
        )

        # Test a course that doesn't have a survey specified
        course2 = Mock(end_of_course_survey_url=None)
        cert_status = {
            'status': 'notpassing', 'grade': '67',
            'download_url': download_url, 'mode': 'honor'
        }
        self.assertEqual(
            _cert_info(user, course2, cert_status, course_mode),
            {
                'status': 'notpassing',
                'show_disabled_download_button': False,
                'show_download_url': False,
                'show_survey_button': False,
                'grade': '67',
                'mode': 'honor',
                'linked_in_url': None
            }
        )

        # test when the display is unavailable or notpassing, we get the correct results out
        course2.certificates_display_behavior = 'early_no_info'
        cert_status = {'status': 'unavailable'}
        self.assertIsNone(_cert_info(user, course2, cert_status, course_mode))

        cert_status = {
            'status': 'notpassing', 'grade': '67',
            'download_url': download_url,
            'mode': 'honor'
        }
        self.assertIsNone(_cert_info(user, course2, cert_status, course_mode))


@ddt.ddt
class DashboardTest(ModuleStoreTestCase):
    """
    Tests for dashboard utility functions
    """

    def setUp(self):
        super(DashboardTest, self).setUp()
        self.course = CourseFactory.create()
        self.user = UserFactory.create(username="jack", email="jack@fake.edx.org", password='test')
        self.client = Client()
        cache.clear()

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def _check_verification_status_on(self, mode, value):
        """
        Check that the css class and the status message are in the dashboard html.
        """
        CourseModeFactory(mode_slug=mode, course_id=self.course.id)
        CourseEnrollment.enroll(self.user, self.course.location.course_key, mode=mode)

        if mode == 'verified':
            # Simulate a successful verification attempt
            attempt = SoftwareSecurePhotoVerification.objects.create(user=self.user)
            attempt.mark_ready()
            attempt.submit()
            attempt.approve()

        response = self.client.get(reverse('dashboard'))
        if mode in ['professional', 'no-id-professional']:
            self.assertContains(response, 'class="course professional"')
        else:
            self.assertContains(response, 'class="course {0}"'.format(mode))
        self.assertContains(response, value)

    @patch.dict("django.conf.settings.FEATURES", {'ENABLE_VERIFIED_CERTIFICATES': True})
    def test_verification_status_visible(self):
        """
        Test that the certificate verification status for courses is visible on the dashboard.
        """
        self.client.login(username="jack", password="test")
        self._check_verification_status_on('verified', 'You\'re enrolled as a verified student')
        self._check_verification_status_on('honor', 'You\'re enrolled as an honor code student')
        self._check_verification_status_on('audit', 'You\'re auditing this course')
        self._check_verification_status_on('professional', 'You\'re enrolled as a professional education student')
        self._check_verification_status_on('no-id-professional', 'You\'re enrolled as a professional education student')

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def _check_verification_status_off(self, mode, value):
        """
        Check that the css class and the status message are not in the dashboard html.
        """
        CourseModeFactory(mode_slug=mode, course_id=self.course.id)
        CourseEnrollment.enroll(self.user, self.course.location.course_key, mode=mode)

        if mode == 'verified':
            # Simulate a successful verification attempt
            attempt = SoftwareSecurePhotoVerification.objects.create(user=self.user)
            attempt.mark_ready()
            attempt.submit()
            attempt.approve()

        response = self.client.get(reverse('dashboard'))
        self.assertNotContains(response, "class=\"course {0}\"".format(mode))
        self.assertNotContains(response, value)

    @patch.dict("django.conf.settings.FEATURES", {'ENABLE_VERIFIED_CERTIFICATES': False})
    def test_verification_status_invisible(self):
        """
        Test that the certificate verification status for courses is not visible on the dashboard
        if the verified certificates setting is off.
        """
        self.client.login(username="jack", password="test")
        self._check_verification_status_off('verified', 'You\'re enrolled as a verified student')
        self._check_verification_status_off('honor', 'You\'re enrolled as an honor code student')
        self._check_verification_status_off('audit', 'You\'re auditing this course')

    def test_course_mode_info(self):
        verified_mode = CourseModeFactory.create(
            course_id=self.course.id,
            mode_slug='verified',
            mode_display_name='Verified',
            expiration_datetime=datetime.now(pytz.UTC) + timedelta(days=1)
        )
        enrollment = CourseEnrollment.enroll(self.user, self.course.id)
        course_mode_info = complete_course_mode_info(self.course.id, enrollment)
        self.assertTrue(course_mode_info['show_upsell'])
        self.assertEquals(course_mode_info['days_for_upsell'], 1)

        verified_mode.expiration_datetime = datetime.now(pytz.UTC) + timedelta(days=-1)
        verified_mode.save()
        course_mode_info = complete_course_mode_info(self.course.id, enrollment)
        self.assertFalse(course_mode_info['show_upsell'])
        self.assertIsNone(course_mode_info['days_for_upsell'])

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_refundable(self):
        verified_mode = CourseModeFactory.create(
            course_id=self.course.id,
            mode_slug='verified',
            mode_display_name='Verified',
            expiration_datetime=datetime.now(pytz.UTC) + timedelta(days=1)
        )
        enrollment = CourseEnrollment.enroll(self.user, self.course.id, mode='verified')

        self.assertTrue(enrollment.refundable())

        verified_mode.expiration_datetime = datetime.now(pytz.UTC) - timedelta(days=1)
        verified_mode.save()
        self.assertFalse(enrollment.refundable())

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    @patch('courseware.views.log.warning')
    @patch.dict('django.conf.settings.FEATURES', {'ENABLE_PAID_COURSE_REGISTRATION': True})
    def test_blocked_course_scenario(self, log_warning):

        self.client.login(username="jack", password="test")

        #create testing invoice 1
        sale_invoice_1 = shoppingcart.models.Invoice.objects.create(
            total_amount=1234.32, company_name='Test1', company_contact_name='Testw',
            company_contact_email='test1@test.com', customer_reference_number='2Fwe23S',
            recipient_name='Testw_1', recipient_email='test2@test.com', internal_reference="A",
            course_id=self.course.id, is_valid=False
        )
        invoice_item = shoppingcart.models.CourseRegistrationCodeInvoiceItem.objects.create(
            invoice=sale_invoice_1,
            qty=1,
            unit_price=1234.32,
            course_id=self.course.id
        )
        course_reg_code = shoppingcart.models.CourseRegistrationCode(
            code="abcde", course_id=self.course.id, created_by=self.user, invoice=sale_invoice_1, invoice_item=invoice_item, mode_slug='honor'
        )
        course_reg_code.save()

        cart = shoppingcart.models.Order.get_cart_for_user(self.user)
        shoppingcart.models.PaidCourseRegistration.add_to_order(cart, self.course.id)
        resp = self.client.post(reverse('shoppingcart.views.use_code'), {'code': course_reg_code.code})
        self.assertEqual(resp.status_code, 200)

        redeem_url = reverse('register_code_redemption', args=[course_reg_code.code])
        response = self.client.get(redeem_url)
        self.assertEquals(response.status_code, 200)
        # check button text
        self.assertTrue('Activate Course Enrollment' in response.content)

        #now activate the user by enrolling him/her to the course
        response = self.client.post(redeem_url)
        self.assertEquals(response.status_code, 200)

        response = self.client.get(reverse('dashboard'))
        self.assertIn('You can no longer access this course because payment has not yet been received', response.content)
        optout_object = Optout.objects.filter(user=self.user, course_id=self.course.id)
        self.assertEqual(len(optout_object), 1)

        # Direct link to course redirect to user dashboard
        self.client.get(reverse('courseware', kwargs={"course_id": self.course.id.to_deprecated_string()}))
        log_warning.assert_called_with(
            u'User %s cannot access the course %s because payment has not yet been received', self.user, self.course.id.to_deprecated_string())

        # Now re-validating the invoice
        invoice = shoppingcart.models.Invoice.objects.get(id=sale_invoice_1.id)
        invoice.is_valid = True
        invoice.save()

        response = self.client.get(reverse('dashboard'))
        self.assertNotIn('You can no longer access this course because payment has not yet been received', response.content)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_refundable_of_purchased_course(self):

        self.client.login(username="jack", password="test")
        CourseModeFactory.create(
            course_id=self.course.id,
            mode_slug='honor',
            min_price=10,
            currency='usd',
            mode_display_name='honor',
            expiration_datetime=datetime.now(pytz.UTC) + timedelta(days=1)
        )
        enrollment = CourseEnrollment.enroll(self.user, self.course.id, mode='honor')

        # TODO: Until we can allow course administrators to define a refund period for paid for courses show_refund_option should be False. # pylint: disable=fixme
        self.assertFalse(enrollment.refundable())

        resp = self.client.post(reverse('student.views.dashboard', args=[]))
        self.assertIn('You will not be refunded the amount you paid.', resp.content)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_refundable_when_certificate_exists(self):
        CourseModeFactory.create(
            course_id=self.course.id,
            mode_slug='verified',
            mode_display_name='Verified',
            expiration_datetime=datetime.now(pytz.UTC) + timedelta(days=1)
        )

        enrollment = CourseEnrollment.enroll(self.user, self.course.id, mode='verified')

        self.assertTrue(enrollment.refundable())

        GeneratedCertificateFactory.create(
            user=self.user,
            course_id=self.course.id,
            status=CertificateStatuses.downloadable,
            mode='verified'
        )

        self.assertFalse(enrollment.refundable())

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_linked_in_add_to_profile_btn_not_appearing_without_config(self):
        # Without linked-in config don't show Add Certificate to LinkedIn button
        self.client.login(username="jack", password="test")

        CourseModeFactory.create(
            course_id=self.course.id,
            mode_slug='verified',
            mode_display_name='verified',
            expiration_datetime=datetime.now(pytz.UTC) - timedelta(days=1)
        )

        CourseEnrollment.enroll(self.user, self.course.id, mode='honor')

        self.course.start = datetime.now(pytz.UTC) - timedelta(days=2)
        self.course.end = datetime.now(pytz.UTC) - timedelta(days=1)
        self.course.display_name = u"Omega"
        self.course = self.update_course(self.course, self.user.id)

        download_url = 'www.edx.org'
        GeneratedCertificateFactory.create(
            user=self.user,
            course_id=self.course.id,
            status=CertificateStatuses.downloadable,
            mode='honor',
            grade='67',
            download_url=download_url
        )
        response = self.client.get(reverse('dashboard'))

        self.assertEquals(response.status_code, 200)
        self.assertNotIn('Add Certificate to LinkedIn', response.content)

        response_url = 'http://www.linkedin.com/profile/add?_ed='
        self.assertNotContains(response, response_url)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    @patch.dict('django.conf.settings.FEATURES', {'CERTIFICATES_HTML_VIEW': False})
    def test_linked_in_add_to_profile_btn_with_certificate(self):
        # If user has a certificate with valid linked-in config then Add Certificate to LinkedIn button
        # should be visible. and it has URL value with valid parameters.
        self.client.login(username="jack", password="test")
        LinkedInAddToProfileConfiguration(
            company_identifier='0_mC_o2MizqdtZEmkVXjH4eYwMj4DnkCWrZP_D9',
            enabled=True
        ).save()

        CourseModeFactory.create(
            course_id=self.course.id,
            mode_slug='verified',
            mode_display_name='verified',
            expiration_datetime=datetime.now(pytz.UTC) - timedelta(days=1)
        )

        CourseEnrollment.enroll(self.user, self.course.id, mode='honor')

        self.course.start = datetime.now(pytz.UTC) - timedelta(days=2)
        self.course.end = datetime.now(pytz.UTC) - timedelta(days=1)
        self.course.display_name = u"Omega"
        self.course = self.update_course(self.course, self.user.id)

        download_url = 'www.edx.org'
        GeneratedCertificateFactory.create(
            user=self.user,
            course_id=self.course.id,
            status=CertificateStatuses.downloadable,
            mode='honor',
            grade='67',
            download_url=download_url
        )
        response = self.client.get(reverse('dashboard'))

        self.assertEquals(response.status_code, 200)
        self.assertIn('Add Certificate to LinkedIn', response.content)

        expected_url = (
            'http://www.linkedin.com/profile/add'
            '?_ed=0_mC_o2MizqdtZEmkVXjH4eYwMj4DnkCWrZP_D9&'
            'pfCertificationName=edX+Honor+Code+Certificate+for+Omega&'
            'pfCertificationUrl=www.edx.org&'
            'source=o'
        )
        self.assertContains(response, expected_url)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    @ddt.data(ModuleStoreEnum.Type.mongo, ModuleStoreEnum.Type.split)
    def test_dashboard_metadata_caching(self, modulestore_type):
        """
        Check that the student dashboard makes use of course metadata caching.

        After creating a course, that course's metadata should be cached as a
        CourseOverview. The student dashboard should never have to make calls to
        the modulestore.

        Arguments:
            modulestore_type (ModuleStoreEnum.Type): Type of modulestore to create
                test course in.

        Note to future developers:
            If you break this test so that the "check_mongo_calls(0)" fails,
            please do NOT change it to "check_mongo_calls(n>1)". Instead, change
            your code to not load courses from the module store. This may
            involve adding fields to CourseOverview so that loading a full
            CourseDescriptor isn't necessary.
        """
        # Create a course and log in the user.
        # Creating a new course will trigger a publish event and the course will be cached
        test_course = CourseFactory.create(default_store=modulestore_type, emit_signals=True)
        self.client.login(username="jack", password="test")

        with check_mongo_calls(0):
            CourseEnrollment.enroll(self.user, test_course.id)

        # Subsequent requests will only result in SQL queries to load the
        # CourseOverview object that has been created.
        with check_mongo_calls(0):
            response_1 = self.client.get(reverse('dashboard'))
            self.assertEquals(response_1.status_code, 200)
            response_2 = self.client.get(reverse('dashboard'))
            self.assertEquals(response_2.status_code, 200)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    @patch.dict(settings.FEATURES, {"IS_EDX_DOMAIN": True})
    def test_dashboard_header_nav_has_find_courses(self):
        self.client.login(username="jack", password="test")
        response = self.client.get(reverse("dashboard"))

        # "Find courses" is shown in the side panel
        self.assertContains(response, "Find courses")

        # But other links are hidden in the navigation
        self.assertNotContains(response, "How it Works")
        self.assertNotContains(response, "Schools & Partners")


class UserSettingsEventTestMixin(EventTestMixin):
    """
    Mixin for verifying that user setting events were emitted during a test.
    """
    def setUp(self):
        super(UserSettingsEventTestMixin, self).setUp('util.model_utils.tracker')

    def assert_user_setting_event_emitted(self, **kwargs):
        """
        Helper method to assert that we emit the expected user settings events.

        Expected settings are passed in via `kwargs`.
        """
        if 'truncated' not in kwargs:
            kwargs['truncated'] = []
        self.assert_event_emitted(
            USER_SETTINGS_CHANGED_EVENT_NAME,
            table=self.table,
            user_id=self.user.id,
            **kwargs
        )


class EnrollmentEventTestMixin(EventTestMixin):
    """ Mixin with assertions for validating enrollment events. """
    def setUp(self):
        super(EnrollmentEventTestMixin, self).setUp('student.models.tracker')

    def assert_enrollment_mode_change_event_was_emitted(self, user, course_key, mode):
        """Ensures an enrollment mode change event was emitted"""
        self.mock_tracker.emit.assert_called_once_with(  # pylint: disable=maybe-no-member
            'edx.course.enrollment.mode_changed',
            {
                'course_id': course_key.to_deprecated_string(),
                'user_id': user.pk,
                'mode': mode
            }
        )
        self.mock_tracker.reset_mock()

    def assert_enrollment_event_was_emitted(self, user, course_key):
        """Ensures an enrollment event was emitted since the last event related assertion"""
        self.mock_tracker.emit.assert_called_once_with(  # pylint: disable=maybe-no-member
            'edx.course.enrollment.activated',
            {
                'course_id': course_key.to_deprecated_string(),
                'user_id': user.pk,
                'mode': 'honor'
            }
        )
        self.mock_tracker.reset_mock()

    def assert_unenrollment_event_was_emitted(self, user, course_key):
        """Ensures an unenrollment event was emitted since the last event related assertion"""
        self.mock_tracker.emit.assert_called_once_with(  # pylint: disable=maybe-no-member
            'edx.course.enrollment.deactivated',
            {
                'course_id': course_key.to_deprecated_string(),
                'user_id': user.pk,
                'mode': 'honor'
            }
        )
        self.mock_tracker.reset_mock()


class EnrollInCourseTest(EnrollmentEventTestMixin, TestCase):
    """Tests enrolling and unenrolling in courses."""

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_enrollment(self):
        user = User.objects.create_user("joe", "joe@joe.com", "password")
        course_id = SlashSeparatedCourseKey("edX", "Test101", "2013")
        course_id_partial = SlashSeparatedCourseKey("edX", "Test101", None)

        # Test basic enrollment
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assertFalse(CourseEnrollment.is_enrolled_by_partial(user, course_id_partial))
        CourseEnrollment.enroll(user, course_id)
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assertTrue(CourseEnrollment.is_enrolled_by_partial(user, course_id_partial))
        self.assert_enrollment_event_was_emitted(user, course_id)

        # Enrolling them again should be harmless
        CourseEnrollment.enroll(user, course_id)
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assertTrue(CourseEnrollment.is_enrolled_by_partial(user, course_id_partial))
        self.assert_no_events_were_emitted()

        # Now unenroll the user
        CourseEnrollment.unenroll(user, course_id)
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assertFalse(CourseEnrollment.is_enrolled_by_partial(user, course_id_partial))
        self.assert_unenrollment_event_was_emitted(user, course_id)

        # Unenrolling them again should also be harmless
        CourseEnrollment.unenroll(user, course_id)
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assertFalse(CourseEnrollment.is_enrolled_by_partial(user, course_id_partial))
        self.assert_no_events_were_emitted()

        # The enrollment record should still exist, just be inactive
        enrollment_record = CourseEnrollment.objects.get(
            user=user,
            course_id=course_id
        )
        self.assertFalse(enrollment_record.is_active)

        # Make sure mode is updated properly if user unenrolls & re-enrolls
        enrollment = CourseEnrollment.enroll(user, course_id, "verified")
        self.assertEquals(enrollment.mode, "verified")
        CourseEnrollment.unenroll(user, course_id)
        enrollment = CourseEnrollment.enroll(user, course_id, "audit")
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assertEquals(enrollment.mode, "audit")

    def test_enrollment_non_existent_user(self):
        # Testing enrollment of newly unsaved user (i.e. no database entry)
        user = User(username="rusty", email="rusty@fake.edx.org")
        course_id = SlashSeparatedCourseKey("edX", "Test101", "2013")

        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))

        # Unenroll does nothing
        CourseEnrollment.unenroll(user, course_id)
        self.assert_no_events_were_emitted()

        # Implicit save() happens on new User object when enrolling, so this
        # should still work
        CourseEnrollment.enroll(user, course_id)
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_enrollment_event_was_emitted(user, course_id)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_enrollment_by_email(self):
        user = User.objects.create(username="jack", email="jack@fake.edx.org")
        course_id = SlashSeparatedCourseKey("edX", "Test101", "2013")

        CourseEnrollment.enroll_by_email("jack@fake.edx.org", course_id)
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_enrollment_event_was_emitted(user, course_id)

        # This won't throw an exception, even though the user is not found
        self.assertIsNone(
            CourseEnrollment.enroll_by_email("not_jack@fake.edx.org", course_id)
        )
        self.assert_no_events_were_emitted()

        self.assertRaises(
            User.DoesNotExist,
            CourseEnrollment.enroll_by_email,
            "not_jack@fake.edx.org",
            course_id,
            ignore_errors=False
        )
        self.assert_no_events_were_emitted()

        # Now unenroll them by email
        CourseEnrollment.unenroll_by_email("jack@fake.edx.org", course_id)
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_unenrollment_event_was_emitted(user, course_id)

        # Harmless second unenroll
        CourseEnrollment.unenroll_by_email("jack@fake.edx.org", course_id)
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_no_events_were_emitted()

        # Unenroll on non-existent user shouldn't throw an error
        CourseEnrollment.unenroll_by_email("not_jack@fake.edx.org", course_id)
        self.assert_no_events_were_emitted()

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_enrollment_multiple_classes(self):
        user = User(username="rusty", email="rusty@fake.edx.org")
        course_id1 = SlashSeparatedCourseKey("edX", "Test101", "2013")
        course_id2 = SlashSeparatedCourseKey("MITx", "6.003z", "2012")

        CourseEnrollment.enroll(user, course_id1)
        self.assert_enrollment_event_was_emitted(user, course_id1)
        CourseEnrollment.enroll(user, course_id2)
        self.assert_enrollment_event_was_emitted(user, course_id2)
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id1))
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id2))

        CourseEnrollment.unenroll(user, course_id1)
        self.assert_unenrollment_event_was_emitted(user, course_id1)
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id1))
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id2))

        CourseEnrollment.unenroll(user, course_id2)
        self.assert_unenrollment_event_was_emitted(user, course_id2)
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id1))
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id2))

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_activation(self):
        user = User.objects.create(username="jack", email="jack@fake.edx.org")
        course_id = SlashSeparatedCourseKey("edX", "Test101", "2013")
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))

        # Creating an enrollment doesn't actually enroll a student
        # (calling CourseEnrollment.enroll() would have)
        enrollment = CourseEnrollment.get_or_create_enrollment(user, course_id)
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_no_events_were_emitted()

        # Until you explicitly activate it
        enrollment.activate()
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_enrollment_event_was_emitted(user, course_id)

        # Activating something that's already active does nothing
        enrollment.activate()
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_no_events_were_emitted()

        # Now deactive
        enrollment.deactivate()
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_unenrollment_event_was_emitted(user, course_id)

        # Deactivating something that's already inactive does nothing
        enrollment.deactivate()
        self.assertFalse(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_no_events_were_emitted()

        # A deactivated enrollment should be activated if enroll() is called
        # for that user/course_id combination
        CourseEnrollment.enroll(user, course_id)
        self.assertTrue(CourseEnrollment.is_enrolled(user, course_id))
        self.assert_enrollment_event_was_emitted(user, course_id)

    def test_change_enrollment_modes(self):
        user = User.objects.create(username="justin", email="jh@fake.edx.org")
        course_id = SlashSeparatedCourseKey("edX", "Test101", "2013")

        CourseEnrollment.enroll(user, course_id)
        self.assert_enrollment_event_was_emitted(user, course_id)

        CourseEnrollment.enroll(user, course_id, "audit")
        self.assert_enrollment_mode_change_event_was_emitted(user, course_id, "audit")

        # same enrollment mode does not emit an event
        CourseEnrollment.enroll(user, course_id, "audit")
        self.assert_no_events_were_emitted()

        CourseEnrollment.enroll(user, course_id, "honor")
        self.assert_enrollment_mode_change_event_was_emitted(user, course_id, "honor")


@unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
class ChangeEnrollmentViewTest(ModuleStoreTestCase):
    """Tests the student.views.change_enrollment view"""

    def setUp(self):
        super(ChangeEnrollmentViewTest, self).setUp()
        self.course = CourseFactory.create()
        self.user = UserFactory.create(password='secret')
        self.client.login(username=self.user.username, password='secret')
        self.url = reverse('change_enrollment')

    def _enroll_through_view(self, course):
        """ Enroll a student in a course. """
        response = self.client.post(
            reverse('change_enrollment'), {
                'course_id': course.id.to_deprecated_string(),
                'enrollment_action': 'enroll'
            }
        )
        return response

    def test_enroll_as_honor(self):
        """Tests that a student can successfully enroll through this view"""
        response = self._enroll_through_view(self.course)
        self.assertEqual(response.status_code, 200)
        enrollment_mode, is_active = CourseEnrollment.enrollment_mode_for_user(
            self.user, self.course.id
        )
        self.assertTrue(is_active)
        self.assertEqual(enrollment_mode, u'honor')

    def test_cannot_enroll_if_already_enrolled(self):
        """
        Tests that a student will not be able to enroll through this view if
        they are already enrolled in the course
        """
        CourseEnrollment.enroll(self.user, self.course.id)
        self.assertTrue(CourseEnrollment.is_enrolled(self.user, self.course.id))
        # now try to enroll that student
        response = self._enroll_through_view(self.course)
        self.assertEqual(response.status_code, 400)

    def test_change_to_honor_if_verified(self):
        """
        Tests that a student that is a currently enrolled verified student cannot
        accidentally change their enrollment to verified
        """
        CourseEnrollment.enroll(self.user, self.course.id, mode=u'verified')
        self.assertTrue(CourseEnrollment.is_enrolled(self.user, self.course.id))
        # now try to enroll the student in the honor mode:
        response = self._enroll_through_view(self.course)
        self.assertEqual(response.status_code, 400)
        enrollment_mode, is_active = CourseEnrollment.enrollment_mode_for_user(
            self.user, self.course.id
        )
        self.assertTrue(is_active)
        self.assertEqual(enrollment_mode, u'verified')

    def test_change_to_honor_if_verified_not_active(self):
        """
        Tests that one can renroll for a course if one has already unenrolled
        """
        # enroll student
        CourseEnrollment.enroll(self.user, self.course.id, mode=u'verified')
        # now unenroll student:
        CourseEnrollment.unenroll(self.user, self.course.id)
        # check that they are verified but inactive
        enrollment_mode, is_active = CourseEnrollment.enrollment_mode_for_user(
            self.user, self.course.id
        )
        self.assertFalse(is_active)
        self.assertEqual(enrollment_mode, u'verified')
        # now enroll them through the view:
        response = self._enroll_through_view(self.course)
        self.assertEqual(response.status_code, 200)
        enrollment_mode, is_active = CourseEnrollment.enrollment_mode_for_user(
            self.user, self.course.id
        )
        self.assertTrue(is_active)
        self.assertEqual(enrollment_mode, u'honor')


class AnonymousLookupTable(ModuleStoreTestCase):
    """
    Tests for anonymous_id_functions
    """
    def setUp(self):
        super(AnonymousLookupTable, self).setUp()
        self.course = CourseFactory.create()
        self.user = UserFactory()
        CourseModeFactory.create(
            course_id=self.course.id,
            mode_slug='honor',
            mode_display_name='Honor Code',
        )
        patcher = patch('student.models.tracker')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_for_unregistered_user(self):  # same path as for logged out user
        self.assertEqual(None, anonymous_id_for_user(AnonymousUser(), self.course.id))
        self.assertIsNone(user_by_anonymous_id(None))

    def test_roundtrip_for_logged_user(self):
        CourseEnrollment.enroll(self.user, self.course.id)
        anonymous_id = anonymous_id_for_user(self.user, self.course.id)
        real_user = user_by_anonymous_id(anonymous_id)
        self.assertEqual(self.user, real_user)
        self.assertEqual(anonymous_id, anonymous_id_for_user(self.user, self.course.id, save=False))

    def test_roundtrip_with_unicode_course_id(self):
        course2 = CourseFactory.create(display_name=u"Omega Course Ω")
        CourseEnrollment.enroll(self.user, course2.id)
        anonymous_id = anonymous_id_for_user(self.user, course2.id)
        real_user = user_by_anonymous_id(anonymous_id)
        self.assertEqual(self.user, real_user)
        self.assertEqual(anonymous_id, anonymous_id_for_user(self.user, course2.id, save=False))
