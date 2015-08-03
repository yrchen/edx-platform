"""
URLs for support dashboard
"""
from django.conf.urls import patterns, url

from support import views

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name="index")
)
