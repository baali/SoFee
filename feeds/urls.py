from django.conf.urls import url
from views import *

urlpatterns = [
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
]
