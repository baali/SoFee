from django.core.management.base import BaseCommand, CommandError
from feeds.models import AuthTokens, TwitterAccounts
from feeds.tasks import rss_task
import tweepy
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('keys.cfg')
import time

class Command(BaseCommand):
    help = '''Given a user screen-name gets all the people user is following and
add them to TwitterAccounts table to be picked up by celery scheduler task.'''

    def add_arguments(self, parser):
        parser.add_argument('screen_name', type=str)

    def handle(self, *args, **options):
        screen_name = options['screen_name']
        try:
            auth_token = AuthTokens.objects.get(screen_name=screen_name)
        except AuthTokens.DoesNotExist:
            raise CommandError('Account "%s" is not yet authorized with the app' % screen_name)
        auth = tweepy.OAuthHandler(config.get('twitter', 'consumer_key'), config.get('twitter', 'consumer_secret'))
        auth.set_access_token(auth_token.access_token, auth_token.access_token_secret)
        try:
            api = tweepy.API(auth, wait_on_rate_limit=True)
        except tweepy.TweepError:
            raise 'Error! Failed to get access token for user %s.' %account.screen_name
        for friend in tweepy.Cursor(api.friends).items():
            if not friend.url:
                continue
            if TwitterAccounts.objects.filter(screen_name=friend.screen_name).exists():
                continue
            timeline = friend.timeline()
            statuses = [status for status in timeline if status.author.screen_name == friend.screen_name]
            if statuses:
                last_updated = statuses[0].created_at
            else:
                last_updated = datetime.datetime.now()
            twitter_account = TwitterAccounts.objects.create(screen_name=friend.screen_name, followed_from=auth_token, last_updated=last_updated)
            try:
                twitter_account.save()
            except:
                raise 'Issue with friend %s' %friend.screen_name
            rss_task.apply_async([friend.url, friend.screen_name, friend.name, friend.id_str, statuses])
