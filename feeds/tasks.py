import tweepy
import time
from tweet_d_feed.celery import app
from feedgen.feed import FeedGenerator
import pytz
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.dom import minidom
import datetime
import ConfigParser
# Create your views here.
config = ConfigParser.RawConfigParser()
config.read('keys.cfg')
from models import AuthTokens, TwitterAccounts
from django.contrib.staticfiles.templatetags.staticfiles import static

@app.task(bind=True)
def update_rss_task(self):
    for account in TwitterAccounts.objects.all():
        auth = tweepy.OAuthHandler(config.get('twitter', 'consumer_key'), config.get('twitter', 'consumer_secret'))
        auth_token = account.followed_from
        auth.set_access_token(auth_token.access_token, auth_token.access_token_secret)
        try:
            api = tweepy.API(auth, wait_on_rate_limit=True)
        except tweepy.TweepError:
            print 'Error! Failed to get access token for user %s.' %account.screen_name
            continue
        statuses = api.user_timeline(screen_name=account.screen_name)
        name = friend_url = screen_name = None
        for status in statuses:
            if pytz.utc.localize(status.created_at) < account.last_updated:
                break
            if status.author.screen_name == account.screen_name:
                # skipping tweets where someone else is talking to friend
                name = status.author.name
                friend_url = status.author.url
                screen_name = status.author.screen_name
                break
        # condition when user has not added anything to the timeline
        # since we last parsed their timeline
        if screen_name == None:
            continue
        fg = FeedGenerator(name)
        fg.id(friend_url)
        fg.description('Tweets by ' + name)
        fg.title(screen_name)
        fg.author( {'name':name} )
        fg.link( href=friend_url, rel='alternate' )
        fg.language('en')
        # get 10 time line activities for the friend
        count = 0
        current_group = None
        for status in statuses:
            if not status.author.screen_name == account.screen_name:
                # skipping tweets where someone else is talking to friend
                continue
            if status.created_at < account.last_updated:
                break
            screen_name = status.author.screen_name
            if getattr(status, 'retweeted_status', None) and status.text.endswith(u'\u2026'):
                text = status.retweeted_status.text
            else:
                text = status.text
            created = status.created_at
            url = 'https://twitter.com/'+screen_name+'/status/'+status.id_str
            fe = fg.add_entry()
            fe.id(url)
            fe.author({'name':name})
            fe.title(text)
            fe.description(text)
            fe.pubdate(pytz.utc.localize(status.created_at))
            account.last_updated = status.created_at
            count += 1
        account.save()
        with open('feeds/static/xml/feed-%s.xml'%account.screen_name, 'w') as feed:
            feed.write(fg.rss_str())
            print 'Done getting status for user: %s' %account.name

@app.task(bind=True)
def rss_task(self, friend_url, screen_name, name, friend_id, timeline):
    fg = FeedGenerator()
    fg.id(friend_url)
    fg.description('Tweets by ' + name)
    fg.title(screen_name)
    fg.author( {'name':name} )
    fg.link( href=friend_url, rel='alternate' )
    fg.language('en')
    # get 10 time line activities for the friend
    count = 0
    current_group = None
    for status in timeline:
        if not status.author.id_str == friend_id:
            # skipping tweets where someone else is talking to friend
            continue
        if getattr(status, 'retweeted_status', None) and status.text.endswith(u'\u2026'):
            text = status.retweeted_status.text
        else:
            text = status.text
        created = status.created_at
        url = 'https://twitter.com/'+screen_name+'/status/'+status.id_str
        fe = fg.add_entry()
        fe.id(url)
        fe.author({'name':name})
        fe.title(text)
        fe.description(text)
        fe.pubdate(pytz.utc.localize(status.created_at))
        count += 1
    with open('feeds/static/xml/feed-%s.xml'%screen_name, 'w') as feed:
        feed.write(fg.rss_str())
        print 'Done getting status for user: %s' %name

@app.task(bind=True)
def opml_task(self, token, verifier, host_uri):
    auth = tweepy.OAuthHandler(config.get('twitter', 'consumer_key'), config.get('twitter', 'consumer_secret'))
    auth.request_token = token
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        print 'Error! Failed to get access token.'
        raise
    try:
        api = tweepy.API(auth, wait_on_rate_limit=True)
    except tweepy.TweepError:
        print 'Error! Failed to get access token.'
        raise
    me = api.me()
    auth_token, created = AuthTokens.objects.get_or_create(screen_name=me.screen_name)
    auth_token.access_token=auth.access_token
    auth_token.access_token_secret=auth.access_token_secret
    auth_token.save()
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
    print ElementTree.tostring(root)
    count = 0
    for friend in tweepy.Cursor(api.friends).items():
        count += 1
        if not friend.url:
            continue
        print 'Processing user %s' %friend.name
        if friend.url:
            meta = {'info': 'Processing user %s' %friend.name,
                    'count': count,
                    'total': me.friends_count,
                }
            self.update_state( state='PROGRESS', meta=meta )
            # timeline = friend.timeline()
            # rss_task.apply_async([friend.url, friend.screen_name, friend.name, friend.id_str, timeline])
            entry = SubElement(body, 'outline',
                               {'text':friend.name,
                                'title':friend.name,
                                'type':'rss',
                                'htmlUrl':friend.url,
                                'xmlUrl':host_uri+static('xml/feed-%s.xml'%friend.screen_name),
                            })
            # Rate limiting(??)
            time.sleep(.5)
    with open('feeds/static/opml/%s.opml'%me.screen_name, 'w') as opml:
        rough_string = ElementTree.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        opml.write(reparsed.toprettyxml(indent="  ").encode('utf8'))
    api.send_direct_message(screen_name=me.screen_name, 
                            text='''Hey there! We just finished compiling OPML file of the RSS feed
based on people you follow. You can access it here
%s Use this file with any feed
reader of you choice.'''%(host_uri+static('opml/'+me.screen_name+'.opml')))
    return host_uri+static('opml/'+me.screen_name+'.opml')
