from django.conf.urls import url

from feeds import views

urlpatterns = [
    url (
        r'^$',
        views.index,
        name='index',
    ),
    url (
        r'^opml/$',
        views.get_opml,
        name='get_feeds',
    ),
    url (
        r'^verify/$',
        views.get_verification,
        name='auth_api',
    ),
    url (
        r'^get_status/$',
        views.get_status,
        name='get_status',
    ),
]
