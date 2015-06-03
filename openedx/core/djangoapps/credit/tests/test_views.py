"""
Tests for credit app views.
"""
import json
import datetime
import pytz

import ddt
from django.test import TestCase
from django.core.urlresolvers import reverse

from student.tests.factories import UserFactory
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.credit import api
from openedx.core.djangoapps.credit.models import (
    CreditCourse,
    CreditProvider,
    CreditRequirement,
    CreditRequirementStatus,
    CreditEligibility,
)


@ddt.ddt
class CreditProviderViewTests(TestCase):
    """
    Tests for HTTP end-points used to issue requests to credit providers
    and receive responses approving or denying requests.
    """

    USERNAME = "ron"
    PASSWORD = "password"
    PROVIDER_ID = "hogwarts"
    COURSE_KEY = CourseKey.from_string("edX/DemoX/Demo_Course")
    FINAL_GRADE = 0.95

    def setUp(self):
        """
        Configure a credit course.
        """
        super(CreditProviderViewTests, self).setUp()

        # Create the test user and log in
        self.user = UserFactory(username=self.USERNAME, password=self.PASSWORD)
        success = self.client.login(username=self.USERNAME, password=self.PASSWORD)
        self.assertTrue(success, msg="Could not log in")

        # Enable the course for credit
        credit_course = CreditCourse.objects.create(
            course_key=self.COURSE_KEY,
            enabled=True,
        )

        # Configure a credit provider for the course
        credit_provider = CreditProvider.objects.create(provider_id=self.PROVIDER_ID)
        credit_course.providers.add(credit_provider)
        credit_course.save()

        # Add a single credit requirement (final grade)
        requirement = CreditRequirement.objects.create(
            course=credit_course,
            namespace="grade",
            name="grade",
        )

        # Mark the user as having satisfied the requirement
        # and eligible for credit.
        CreditRequirementStatus.objects.create(
            username=self.USERNAME,
            requirement=requirement,
            status="satisfied",
            reason={"final_grade": self.FINAL_GRADE}
        )
        CreditEligibility.objects.create(
            username=self.USERNAME,
            course=credit_course,
            provider=credit_provider,
        )

    def test_credit_request_and_response(self):
        # Initiate a request
        response = self._create_credit_request(self.USERNAME, self.COURSE_KEY)
        self.assertEqual(response.status_code, 200)

        # Check that the user's request status is pending
        requests = api.get_credit_requests_for_user(self.USERNAME)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["status"], "pending")

        # Check request parameters
        content = json.loads(response.content)
        self.assertEqual(content["url"], "TODO")
        self.assertEqual(content["method"], "POST")
        self.assertEqual(len(content["parameters"]["request_uuid"]), 32)
        self.assertEqual(content["parameters"]["course_org"], "TODO")
        self.assertEqual(content["parameters"]["course_num"], "TODO")
        self.assertEqual(content["parameters"]["course_run"], "TODO")
        self.assertEqual(content["parameters"]["final_grade"], 0.95)
        self.assertEqual(content["parameters"]["user_username"], "TODO")
        self.assertEqual(content["parameters"]["user_full_name"], "TODO")
        self.assertEqual(content["parameters"]["user_mailing_address"], "TODO")
        self.assertEqual(content["parameters"]["user_country"], "TODO")
        self.assertEqual(content["parameters"]["signature"], "TODO")

        # Simulate a response from the credit provider
        response = self._credit_provider_callback(
            content["parameters"]["request_uuid"],
            "approved"
        )
        self.assertEqual(response.status_code, 200)

        # Check that the user's status is approved
        requests = api.get_credit_requests_for_user(self.USERNAME)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["status"], "approved")

    def test_request_credit_anonymous_user(self):
        self.client.logout()
        response = self._create_credit_request(self.USERNAME, self.COURSE_KEY)
        self.assertEqual(response.status_code, 403)

    def test_request_credit_for_another_user(self):
        response = self._create_credit_request("another_user", self.COURSE_KEY)
        self.assertEqual(response.status_code, 403)

    @ddt.data(
        # Invalid JSON
        "{",

        # Missing required parameters
        json.dumps({"username": USERNAME}),
        json.dumps({"course_key": unicode(COURSE_KEY)}),
    )
    def test_create_credit_request_invalid_parameters(self, request_data):
        url = reverse("credit_create_request", args=[self.PROVIDER_ID])
        response = self.client.post(url, data=request_data, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def _create_credit_request(self, username, course_key):
        """
        Initiate a request for credit.
        """
        url = reverse("credit_create_request", args=[self.PROVIDER_ID])
        return self.client.post(
            url,
            data=json.dumps({
                "username": username,
                "course_key": unicode(course_key),
            }),
            content_type="application/json",
        )

    def _credit_provider_callback(self, request_uuid, status):
        """
        Simulate a response from the credit provider approving
        or rejecting the credit request.
        """
        url = reverse("credit_provider_callback", args=[self.PROVIDER_ID])
        return self.client.post(
            url,
            data=json.dumps({
                "request_uuid": request_uuid,
                "status": status,
                "timestamp": datetime.datetime.now(pytz.UTC).isoformat(),
                "signature": "TODO"
            }),
            content_type="application/json",
        )
