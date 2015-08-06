"""
Tests for certificate app views used by the support team.
"""

import json

import ddt
from django.core.urlresolvers import reverse
from django.test import TestCase

from opaque_keys.edx.keys import CourseKey
from student.tests.factories import UserFactory
from student.roles import GlobalStaff, SupportStaffRole
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from certificates.models import GeneratedCertificate, CertificateStatuses


class CertificateSupportTestCase(TestCase):
    """TODO """

    SUPPORT_USERNAME = "support"
    SUPPORT_EMAIL = "support@example.com"
    SUPPORT_PASSWORD = "support"

    STUDENT_USERNAME = "student"
    STUDENT_EMAIL = "student@example.com"
    STUDENT_PASSWORD = "student"

    CERT_COURSE_KEY = CourseKey.from_string("edX/DemoX/Demo_Course")
    CERT_GRADE = 0.89
    CERT_STATUS = CertificateStatuses.downloadable
    CERT_MODE = "verified"
    CERT_DOWNLOAD_URL = "http://www.example.com/cert.pdf"

    def setUp(self):
        """TODO """
        super(CertificateSupportTestCase, self).setUp()

        # Create the support staff user
        self.support = UserFactory(
            username=self.SUPPORT_USERNAME,
            email=self.SUPPORT_EMAIL,
            password=self.SUPPORT_PASSWORD,
        )
        SupportStaffRole().add_users(self.support)

        # Create a student
        self.student = UserFactory(
            username=self.STUDENT_USERNAME,
            email=self.STUDENT_EMAIL,
            password=self.STUDENT_PASSWORD,
        )

        # Create certificates for the student
        self.cert = GeneratedCertificate.objects.create(
            user=self.student,
            course_id=self.CERT_COURSE_KEY,
            grade=self.CERT_GRADE,
            status=self.CERT_STATUS,
            mode=self.CERT_MODE,
            download_url=self.CERT_DOWNLOAD_URL,
        )

        # Login as support staff
        success = self.client.login(username=self.SUPPORT_USERNAME, password=self.SUPPORT_PASSWORD)
        self.assertTrue(success, msg="Couldn't log in as support staff")


@ddt.ddt
class CertificateSearchTests(CertificateSupportTestCase):
    """TODO """

    @ddt.data(
        (GlobalStaff, True),
        (SupportStaffRole, True),
        (None, False),
    )
    @ddt.unpack
    def test_access_control(self, role, has_access):
        # Create a user and log in
        user = UserFactory(username="foo", password="foo")
        success = self.client.login(username="foo", password="foo")
        self.assertTrue(success, msg="Could not log in")

        # Assign the user to the role
        if role is not None:
            role().add_users(user)

        # Retrieve the page
        response = self._search("foo")

        if has_access:
            self.assertContains(response, json.dumps([]))
        else:
            self.assertEqual(response.status_code, 403)

    @ddt.data(
        (CertificateSupportTestCase.STUDENT_USERNAME, True),
        (CertificateSupportTestCase.STUDENT_EMAIL, True),
        ("bar", False),
        ("bar@example.com", False),
    )
    @ddt.unpack
    def test_search(self, query, expect_result):
        response = self._search(query)
        self.assertEqual(response.status_code, 200)

        results = json.loads(response.content)
        self.assertEqual(len(results), 1 if expect_result else 0)

    def test_results(self):
        response = self._search(self.STUDENT_USERNAME)
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)

        self.assertEqual(len(results), 1)
        retrieved_cert = results[0]

        self.assertEqual(retrieved_cert["username"], self.STUDENT_USERNAME)
        self.assertEqual(retrieved_cert["course_key"], unicode(self.CERT_COURSE_KEY))
        self.assertEqual(retrieved_cert["created"], self.cert.created_date.isoformat())
        self.assertEqual(retrieved_cert["modified"], self.cert.modified_date.isoformat())
        self.assertEqual(retrieved_cert["grade"], unicode(self.CERT_GRADE))
        self.assertEqual(retrieved_cert["status"], self.CERT_STATUS)
        self.assertEqual(retrieved_cert["type"], self.CERT_MODE)

    def _search(self, query):
        """TODO """
        url = reverse("certificates:search") + "?query=" + query
        return self.client.get(url)


@ddt.ddt
class CertificateRegenerateTests(ModuleStoreTestCase, CertificateSupportTestCase):
    """TODO """

    def setUp(self):
        """TODO """
        super(CertificateRegenerateTests, self).setUp()

    @ddt.data(
        (GlobalStaff, True),
        (SupportStaffRole, True),
        (None, False),
    )
    @ddt.unpack
    def test_access_control(self, role, has_access):
        # Create a user and log in
        user = UserFactory(username="foo", password="foo")
        success = self.client.login(username="foo", password="foo")
        self.assertTrue(success, msg="Could not log in")

        # Assign the user to the role
        if role is not None:
            role().add_users(user)

        # Make a POST request
        # Since we're not passing valid parameters, we'll get an error response
        # but at least we'll know we have access
        url = reverse("certificates:regenerate_certificate_for_user")
        response = self.client.post(url)

        if has_access:
            self.assertEqual(response.status_code, 400)
        else:
            self.assertEqual(response.status_code, 403)

    def test_regenerate_certificate(self):
        self.fail("TODO")

    def test_regenerate_no_such_course(self):
        self.fail("TODO")

    def test_regenerate_user_is_not_enrolled(self):
        self.fail("TODO")

    def test_regenerate_user_has_no_certificate(self):
        self.fail("TODO")
