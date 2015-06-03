"""
Views for the credit Django app.
"""
from django.http import HttpResponse


def create_credit_request(request):
    """
    TODO
    """
    return HttpResponse("Create credit request!")


def credit_provider_callback(request, provider_id):
    """
    TODO
    """
    return HttpResponse("Credit provider callback: " + provider_id)
