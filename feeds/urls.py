from django.conf.urls import url, include
from feeds import views

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
    url(r'^links/(?P<uuid>[a-zA-Z0-9-]+)/$', views.url_list, name='links'),
    url(r'^opml/(?P<uuid>[a-zA-Z0-9-]+)/$', views.opml, name='opml'),
    url(r'^status/(?P<uuid>[a-zA-Z0-9-]+)/$', status_list, name='statuses'),
    url(r'^api-auth/(?P<uuid>[a-zA-Z0-9-]+)/', include('rest_framework.urls', namespace='rest_framework'))
]
