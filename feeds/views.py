from django.conf import settings
from django.shortcuts import redirect, render_to_response
from django.http import JsonResponse, Http404
from rest_framework.serializers import ValidationError
import tweepy
from feeds.tasks import opml_task
from django.contrib.auth import logout
from feeds.models import UrlShared, TwitterStatus, TwitterAccount, AuthToken
from feeds.serializers import UrlSerializer, StatusSerializer
from rest_framework import viewsets, pagination, status
from rest_framework.response import Response
from urllib import parse
from rest_framework.decorators import api_view
from feedgen.feed import FeedGenerator
from xml.etree.ElementTree import Element, SubElement, Comment
from xml.dom import minidom
from xml.etree import ElementTree
import datetime
from django.utils import timezone
from dateutil import parser

session = {}


class CursorPagination(pagination.CursorPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000


@api_view(['GET', 'POST'])
def url_list(request, uuid):
    if request.method == 'GET':
        get_feed = request.query_params.get('feed', None)
        seen = request.query_params.get('seen', False)
        links_of = request.query_params.get('links_of', '')
        if TwitterAccount.objects.filter(followed_from__uuid=uuid).exists():
            accounts = TwitterAccount.objects.filter(followed_from__uuid=uuid)
        else:
            raise Http404
        if get_feed:
            # Function to get RSS feed
            rss_file = ''
            # FIXME: should we use dragnet for getting content of URL?
            screen_name = accounts.first().followed_from.get(uuid=uuid).screen_name
            fg = FeedGenerator()
            fg.id('https://twitter.com/%s'%screen_name)
            fg.description('Links shared by people you follow')
            fg.title(screen_name)
            fg.author({'name': screen_name})
            fg.link(href='https://twitter.com/%s'%screen_name, rel='alternate')
            fg.language('en')
            for link in UrlShared.objects.filter(shared_from__in=[account.uuid for account in accounts]):
                fe = fg.add_entry()
                fe.id(link.url)
                fe.author({'name': ', '.join([shared_from.screen_name for shared_from in link.shared_from.all()])})
                fe.title(link.url)
                fe.description(link.url)
                fe.pubdate(link.url_shared)
            with open('feeds/static/xml/%s-feed.xml' % uuid, 'wb') as feed:
                feed.write(fg.rss_str())
            return Response({'rss': 'SomeFileLocation'}, status=status.HTTP_200_OK)
        else:
            if links_of:
                if TwitterAccount.objects.filter(uuid=links_of):
                    links = UrlShared.objects.filter(shared_from=links_of, url_seen=seen)
                else:
                    raise Http404
            else:
                links = UrlShared.objects.filter(shared_from__in=[account.uuid for account in accounts], url_seen=seen)
            serialized_links = UrlSerializer(links, many=True)
            return Response(serialized_links.data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        url_shared = request.data.get('url_shared', '')
        if uuid:
            try:
                oauth_account = AuthToken.objects.get(uuid=uuid)
                twitter_account = TwitterAccount.objects.get(screen_name=oauth_account.screen_name)
            except AuthToken.DoesNotExist:
                raise ValidationError('You are not authorized to archive link on this service')
            parsed_url = parse.urlparse(url_shared)
            # FIXME: YouTube URLs would be totally screwed by this.
            cleaned_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            if cleaned_url:
                url_obj, created = UrlShared.objects.get_or_create(url=cleaned_url)
                if created:
                    url_obj.save()
                url_obj.shared_from.add(twitter_account)
                url_obj.save()
                serialized_obj = UrlSerializer(url_obj)
                return Response(serialized_obj.data, status=status.HTTP_201_CREATED)
            else:
                raise ValidationError('Missing url.')
        else:
            raise ValidationError('You are not authorized to archive link on this service')


class StatusViewSet(viewsets.ModelViewSet):
    lookup_field = 'followed_from__uuid'
    serializer_class = StatusSerializer
    # pagination_class = CursorPagination

    def get_queryset(self):
        uuid = self.kwargs["uuid"]
        seen = self.request.query_params.get("seen", False)
        if TwitterStatus.objects.filter(followed_from__uuid=uuid).exists():
            # time_threshold = timezone.now() - datetime.timedelta(hours=24)
            if seen:
                statuses = TwitterStatus.objects.filter(followed_from__uuid=uuid)
            else:
                statuses = TwitterStatus.objects.filter(followed_from__uuid=uuid, status_seen=seen)
            return statuses
        else:
            raise Http404


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
        host_uri = 'http://' + request.get_host()
        SubElement(body, 'outline',
                   {'text': 'Links',
                    'title': 'Feeds of all links shared by people you follow.',
                    'type': 'rss',
                    'htmlUrl': host_uri + 'links/%s/'%uuid,
                    'xmlUrl': host_uri + 'links/%s/?feed=1'%uuid,
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
