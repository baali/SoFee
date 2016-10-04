from django.conf.urls import url, include
from feeds import views

url_list = views.LinkViewSet.as_view({
    'get': 'list',
})

status_list = views.StatusViewSet.as_view({
    'get': 'list',
})

urlpatterns = [
    url(
        r'^$',
        views.index,
        name='index',
    ),
    url(
        r'^opml/$',
        views.get_opml,
        name='get_feeds',
    ),
    url(
        r'^verify/$',
        views.get_verification,
        name='auth_api',
    ),
    url(
        r'^get_status/$',
        views.get_status,
        name='get_status',
    ),
    url(r'^links/(?P<uuid>[a-zA-Z0-9-]+)/$', url_list, name='links'),
    url(r'^status/(?P<uuid>[a-zA-Z0-9-]+)/$', status_list, name='statuses'),
    url(r'^api-auth/(?P<uuid>[a-zA-Z0-9-]+)/', include('rest_framework.urls', namespace='rest_framework'))
]
