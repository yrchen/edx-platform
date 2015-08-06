"""
Tests for support views.
"""

import ddt
from django.test import TestCase
from django.core.urlresolvers import reverse

from student.roles import GlobalStaff, SupportStaffRole
from student.tests.factories import UserFactory


class SupportViewTestCase(TestCase):
    """
    TODO
    """

    USERNAME = "support"
    EMAIL = "support@example.com"
    PASSWORD = "support"

    def setUp(self):
        """TODO """
        super(SupportViewTestCase, self).setUp()
        self.user = UserFactory(username=self.USERNAME, email=self.EMAIL, password=self.PASSWORD)
        success = self.client.login(username=self.USERNAME, password=self.PASSWORD)
        self.assertTrue(success, msg="Could not log in")


@ddt.ddt
class SupportViewAccessTests(SupportViewTestCase):
    """
    Tests for access control of support views.
    """

    @ddt.data(
        ("support:index", GlobalStaff, True),
        ("support:index", SupportStaffRole, True),
        ("support:index", None, True),
        ("support:certificates", GlobalStaff, True),
        ("support:certificates", SupportStaffRole, True),
        ("support:certificates", None, True),
        ("support:refund", GlobalStaff, True),
        ("support:refund", SupportStaffRole, True),
        ("support:refund", None, True),
    )
    @ddt.unpack
    def test_access(self, url_name, role, has_access):
        self.fail("TODO")

    @ddt.data("support:index", "support:certificates", "support:refund")
    def test_require_login(self, url_name):
        url = reverse(url_name)

        # Log out then try to retrieve the page
        self.client.logout()
        response = self.client.get(url)

        # Expect a redirect to the login page
        redirect_url = "{login_url}?next={original_url}".format(
            login_url=reverse("signin_user"),
            original_url=url,
        )
        self.assertRedirects(response, redirect_url)


class SupportViewIndexTests(SupportViewTestCase):
    """
    Tests for the support index view.
    """

    def test_index(self):
        self.fail("TODO")


class SupportViewCertificatesTests(SupportViewTestCase):
    """
    TODO
    """

    def test_certificates_no_query(self):
        self.fail("TODO")

    def test_certificates_with_query(self):
        self.fail("TODO")
