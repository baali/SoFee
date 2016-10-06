from django.conf import settings
from django.shortcuts import redirect, render_to_response
from django.http import JsonResponse, Http404

import tweepy
from feeds.tasks import opml_task
from django.contrib.auth import logout
from feeds.models import TwitterLink, TwitterStatus, TwitterAccount
from feeds.serializers import LinkSerializer, StatusSerializer
from rest_framework import viewsets, pagination
from rest_framework.response import Response

session = {}


class CursorPagination(pagination.CursorPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LinkViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = LinkSerializer
    # pagination_class = CursorPagination

    def get_queryset(self):
        uuid = self.kwargs["uuid"]
        get_rss = self.request.query_params.get("rss", None)
        seen = self.request.query_params.get("seen", False)
        if get_rss:
            # Function to get RSS feed
            rss_file = ''
            return Response({'rss': rss_file})
        else:
            if TwitterAccount.objects.filter(followed_from__uuid=uuid).exists():
                accounts = TwitterAccount.objects.filter(followed_from__uuid=uuid)
                links = TwitterLink.objects.filter(shared_from__in=[account.uuid for account in accounts], url_seen=seen)
                return links
            else:
                raise Http404


class StatusViewSet(viewsets.ModelViewSet):
    lookup_field = 'followed_from__uuid'
    serializer_class = StatusSerializer
    # pagination_class = CursorPagination

    def get_queryset(self):
        uuid = self.kwargs["uuid"]
        seen = self.request.query_params.get("seen", False)
        if TwitterStatus.objects.filter(followed_from__uuid=uuid).exists():
            statuses = TwitterStatus.objects.filter(followed_from__uuid=uuid, status_seen=seen)
            return statuses
        else:
            raise Http404


def timeline(request):
    """
    display some user info to show we have authenticated successfully
    """
    if check_key(request):
        auth = tweepy.OAuthHandler(
            settings.TWITTER_CONSUMER_KEY,
            settings.TWITTER_CONSUMER_SECRET)
        access_key = request.session['access_key_tw']
        access_secret = request.session['access_secret_tw']
        auth.set_access_token(access_key, access_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True)
        user = api.me()
        return render_to_response('info.html', {'name': user.screen_name})
    else:
        return redirect('/')


def unauth(request):
    """
    logout and remove all session data
    """
    if check_key(request):
        request.session.clear()
        logout(request)
    return redirect('/')


def check_key(request):
    """
    Check to see if we already have an access_key stored, if we do then we have already gone through
    OAuth. If not then we haven't and we probably need to.
    """
    access_key = request.session.get('access_key_tw', None)
    if not access_key:
        return False
    return True


def index(request):
    return render_to_response('layout.html')


def get_opml(request):
    auth = tweepy.OAuthHandler(
        settings.TWITTER_CONSUMER_KEY,
        settings.TWITTER_CONSUMER_SECRET,
        'http://' + request.get_host() + '/verify/'
    )
    try:
        # get the request tokens
        redirect_url = auth.get_authorization_url()
        session['request_token'] = auth.request_token
        return redirect(redirect_url)

    except tweepy.TweepError as e:
        raise Http404(e)


def get_verification(request):
    # get the verifier key from the request url
    verifier = request.GET.get('oauth_verifier')
    if 'request_token' not in session:
        return redirect('/')
    token = session['request_token']
    job = opml_task.apply_async(
        [token, verifier, 'http://' + request.get_host()])
    session.pop('request_token')
    return render_to_response('layout.html', context={'uuid': '%s' % job.id})


def get_status(request):
    # get the verifier key from the request url
    task_id = request.GET.get('uuid')
    task = opml_task.AsyncResult(task_id)
    if task.state == 'PROGRESS':
        return JsonResponse({'task_status': task.state, 'info': task.info['info'], 'count': task.info['count'], 'total_count': task.info['total']})
    elif task.state == 'FAILURE':
        return JsonResponse({'task_status': task.state, }, status=400)
    elif task.state == 'SUCCESS':
        return JsonResponse({'task_status': task.state, 'info': task.result, })
    else:
        return JsonResponse({'task_status': task.state, 'message': 'It is lost'})
