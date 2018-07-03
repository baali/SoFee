from django.conf import settings
from django.shortcuts import redirect, render_to_response
from django.http import JsonResponse, Http404, HttpResponse
from django.urls import reverse
from rest_framework.serializers import ValidationError
import tweepy
from feeds.tasks import update_accounts_task
from django.contrib.auth import logout
from feeds.models import AuthToken, TwitterAccount, UrlShared, \
    TwitterStatus, PushNotificationToken
from feeds.serializers import UrlSerializer, StatusSerializer, \
    PushNotificationSerializer
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from urllib import parse
from rest_framework.decorators import api_view, detail_route
from feedgen.feed import FeedGenerator
from xml.etree.ElementTree import Element, SubElement, Comment
from xml.dom import minidom
from xml.etree import ElementTree
import datetime
from django.utils import timezone
from dateutil import parser
from django.http import QueryDict
# from django.core.management import call_command
from django.views.decorators.cache import never_cache
from django.template.loader import get_template
from django.template import RequestContext


# http://stackoverflow.com/questions/34389485/implementing-push-notification-using-chrome-in-django
@never_cache
def sw_js(request, js):
    template = get_template('sw.js')
    html = template.render(context={'uuid': request.GET.get('uuid', '')})
    return HttpResponse(html, content_type="application/javascript")


class UrlViewSet(viewsets.ModelViewSet):
    serializer_class = UrlSerializer

    def get_queryset(self):
        uuid = self.kwargs.get('uuid', '')
        if not uuid:
            raise Http404
        if not AuthToken.objects.filter(uuid=uuid).exists():
            raise Http404
        links_of = self.request.query_params.get('links_of', '')
        if links_of:
            if TwitterAccount.objects.filter(uuid=links_of).exists():
                links = UrlShared.objects.filter(shared_from=links_of)
            else:
                raise Http404
        else:
            links = UrlShared.objects.filter(shared_from__followed_from__uuid=uuid)
        return links

    @detail_route()
    def get_feed(self, request, uuid=None):
        if not uuid:
            raise Http404
        if not AuthToken.objects.filter(uuid=uuid).exists():
            raise Http404
        screen_name = AuthToken.objects.get(uuid=uuid).screen_name
        feed_date = parser.parse(self.request.query_params.get('date',
                                                               datetime.date.today().strftime('%d-%b-%Y')))
        fg = FeedGenerator()
        fg.id('https://twitter.com/%s' % screen_name)
        fg.description('Links shared by people you follow')
        fg.title(screen_name)
        fg.author({'name': screen_name})
        fg.link(href='https://twitter.com/%s' % screen_name, rel='alternate')
        fg.language('en')
        for link in UrlShared.objects.filter(shared_from__followed_from__uuid=uuid, url_shared__gte=feed_date).order_by('url').distinct('url'):
            fe = fg.add_entry()
            fe.id(link.url)
            fe.author({'name': ', '.join([shared_from.screen_name for shared_from in link.shared_from.all()])})
            fe.title(link.url)
            fe.content(link.url)
            fe.pubdate(link.url_shared)
        with open('feeds/static/xml/%s-feed.xml' % uuid, 'wb') as feed:
            feed.write(fg.atom_str(pretty=True))
        return Response({'xml_file': 'xml/%s-feed.xml' % uuid,
                         'date': feed_date.strftime('%d %b %Y')},
                        status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def share_url(self, request, uuid=None):
        if not uuid:
            raise ValidationError('You are not authorized to archive link on this service')
        if not AuthToken.objects.filter(uuid=uuid).exists():
            raise ValidationError('You are not authorized to archive link on this service')
        url_shared = request.data.get('url_shared', '')
        try:
            oauth_account = AuthToken.objects.get(uuid=uuid)
            twitter_account = TwitterAccount.objects.get(screen_name=oauth_account.screen_name)
        except AuthToken.DoesNotExist:
            raise ValidationError('You are not authorized to archive link on this service')
        parsed_url = parse.urlparse(url_shared)
        # FIXME: YouTube URLs would be totally screwed by this.
        cleaned_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
        if cleaned_url:
            if UrlShared.objects.filter(url=cleaned_url).exists():
                url_obj = UrlShared.objects.get(url=cleaned_url)
            else:
                url_obj = UrlShared.objects.create(url=cleaned_url, url_shared=timezone.now())
            url_obj.shared_from.add(twitter_account)
            url_obj.save()
            serialized_obj = UrlSerializer(url_obj)
            return Response(serialized_obj.data, status=status.HTTP_201_CREATED)
        else:
            raise ValidationError('Missing url.')


class StatusViewSet(viewsets.ModelViewSet):
    serializer_class = StatusSerializer

    def get_queryset(self):
        uuid = self.kwargs["uuid"]
        seen = self.request.query_params.get("seen", False)
        if not AuthToken.objects.filter(uuid=uuid).exists():
            raise Http404
        if seen:
            statuses = TwitterStatus.objects.filter(followed_from__uuid=uuid, status_seen=seen)
        else:
            statuses = TwitterStatus.objects.filter(followed_from__uuid=uuid)
        return statuses


@api_view(['GET'])
def opml(request, uuid):
    if TwitterAccount.objects.filter(followed_from__uuid=uuid).exists():
        root = Element('opml')
        generated_on = str(datetime.datetime.now())
        root.set('version', '1.0')
        root.append(Comment('Feed list of all tweets'))

        head = SubElement(root, 'head')
        title = SubElement(head, 'title')
        title.text = 'My Twitter Feed'
        dc = SubElement(head, 'dateCreated')
        dc.text = generated_on
        dm = SubElement(head, 'dateModified')
        dm.text = generated_on

        body = SubElement(root, 'body')
        host_uri = 'https://' + request.get_host()
        SubElement(body, 'outline',
                   {'text': 'Links',
                    'title': 'Feeds of all links shared by people you follow.',
                    'type': 'rss',
                    'htmlUrl': host_uri + 'links/%s/' % uuid,
                    'xmlUrl': host_uri + 'links/%s/?feed=1' % uuid,
                    })
        with open('feeds/static/opml/%s.opml' % uuid, 'wb') as opml:
            rough_string = ElementTree.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            opml.write(reparsed.toprettyxml(indent="  ").encode('utf8'))
        return Response({'xml_file': 'opml/%s.opml' % uuid}, status=status.HTTP_200_OK)
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


def index(request, uuid=''):
    return render_to_response('layout.html',
                              {'uuid': uuid,
                               'task_id': request.GET.get('task_id', ''),
                               'fcm_web_api_key': settings.FCM_WEB_API_KEY,
                               'fcm_id': settings.FCM_ID},
                              context_instance=RequestContext(request))


def oauth_dance(request):
    auth = tweepy.OAuthHandler(
        settings.TWITTER_CONSUMER_KEY,
        settings.TWITTER_CONSUMER_SECRET,
        'https://' + request.get_host() + '/verify/'
    )
    try:
        # get the request tokens
        redirect_url = auth.get_authorization_url()
        request.session['request_token'] = auth.request_token
        return redirect(redirect_url)

    except tweepy.TweepError as e:
        raise Http404(e)


def get_verification(request):
    # get the verifier key from the request url
    verifier = request.GET.get('oauth_verifier')
    if 'request_token' not in request.session:
        return redirect('/')
    auth = tweepy.OAuthHandler(
        settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)
    auth.request_token = request.session['request_token']
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        raise
    try:
        api = tweepy.API(auth, wait_on_rate_limit=True)
    except tweepy.TweepError:
        raise
    me = api.me()
    auth_token, created = AuthToken.objects.get_or_create(
        screen_name=me.screen_name)
    auth_token.access_token = auth.access_token
    auth_token.access_token_secret = auth.access_token_secret
    auth_token.me_json = me._json
    auth_token.save()

    request.session.pop('request_token')
    job = update_accounts_task.apply_async([str(auth_token.uuid)])
    url = reverse('index', kwargs={'uuid': auth_token.uuid})
    qdict = QueryDict('', mutable=True)
    qdict.update({'task_id': job.id})
    # return render_to_response('layout.html')# , context={'uuid': '%s' % job.id})
    # call_command('poll_twitter', str(auth_token.uuid))
    return redirect(url + '?' + qdict.urlencode())


def get_status(request):
    # get the verifier key from the request url
    task_id = request.GET.get('task_id')
    task = update_accounts_task.AsyncResult(task_id)
    if task.state == 'PROGRESS':
        return JsonResponse({'task_status': task.state, 'info': task.info['info'], 'count': task.info['count'], 'total_count': task.info['total']})
    elif task.state == 'FAILURE':
        return JsonResponse({'task_status': task.state, }, status=400)
    elif task.state == 'SUCCESS':
        return JsonResponse({'task_status': task.state, 'info': task.result, })
    else:
        return JsonResponse({'task_status': task.state, 'message': 'It is lost'})


class PushTokenList(APIView):
    """
    Create PushToken for WebPush.
    """
    def post(self, request, format=None):
        uuid = request.data.get('uuid', '')
        if not uuid:
            raise ValidationError('You are not authorized to archive link on this service')
        try:
            oauth_account = AuthToken.objects.get(uuid=uuid)
            twitter_account = TwitterAccount.objects.get(screen_name=oauth_account.screen_name)
        except AuthToken.DoesNotExist:
            raise ValidationError('You are not authorized to archive link on this service')
        push_token, created = PushNotificationToken.objects.get_or_create(token=request.data['token'],
                                                                          token_for=twitter_account)
        serializer = PushNotificationSerializer(push_token)
        if created:
            push_token.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
