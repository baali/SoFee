from django.conf.urls import url
from views import *
from django.conf.urls import patterns

urlpatterns = patterns(
    '', 
    url (
        r'^$', 
        index, 
        name='index',
    ),
    url (
        r'^opml/$', 
        get_opml, 
        name='get_feeds',
    ),
    url (
        r'^verify/$', 
        get_verification, 
        name='auth_api',
    ),
    url (
        r'^get_status/$', 
        get_status, 
        name='get_status',
    ),
    # url (
    #     r'^rss/$', 
    #     rss_view, 
    #     name='rss',
    # ),
)
