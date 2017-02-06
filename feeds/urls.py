from django.conf.urls import url, include
from feeds import views

status_list = views.StatusViewSet.as_view({
    'get': 'list',
})
url_listing = views.UrlViewSet.as_view({
    'get': 'list',
})
get_feed = views.UrlViewSet.as_view({
    'get': 'get_feed'
})
share_url = views.UrlViewSet.as_view({
    'post': 'share_url'
})

urlpatterns = [
    url(
        r'^$',
        views.index,
        name='index',
    ),
    url(
        r'^authenticate/$',
        views.oauth_dance,
        name='authenticate',
    ),
    url(
        r'^verify/$',
        views.get_verification,
        name='auth_api',
    ),
    url(
        r'^get_task_status/$',
        views.get_status,
        name='get_status',
    ),
    url(r'^index/(?P<uuid>[a-zA-Z0-9-]+)/$', views.index, name='index'),
    url(r'^opml/(?P<uuid>[a-zA-Z0-9-]+)/$', views.opml, name='opml'),
    url(r'^status/(?P<uuid>[a-zA-Z0-9-]+)/$', status_list, name='statuses'),
    url(r'^urls/(?P<uuid>[a-zA-Z0-9-]+)/$', url_listing, name='urls'),
    url(r'^urls/(?P<uuid>[a-zA-Z0-9-]+)/get_feed/$', get_feed, name='get_feed'),
    url(r'^urls/(?P<uuid>[a-zA-Z0-9-]+)/share_url/$', share_url, name='share_url'),
    url(r'^api-auth/(?P<uuid>[a-zA-Z0-9-]+)/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^(.*.js)$', views.sw_js, name='sw_js'),
]
