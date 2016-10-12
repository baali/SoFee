import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import tweepy
import pytz

from feeds.models import AuthToken, TwitterAccount, TwitterStatus, UrlShared


class Command(BaseCommand):
    help = '''Given a user screen-name gets all the people user is following and
add them to TwitterAccounts table to be picked up by celery scheduler task.'''

    def add_arguments(self, parser):
        parser.add_argument('screen_name', type=str)

    def handle(self, *args, **options):
        screen_name = options['screen_name']
        try:
            auth_token = AuthToken.objects.get(screen_name=screen_name)
        except AuthToken.DoesNotExist:
            raise CommandError('Account "%s" is not yet authorized with the app' % screen_name)

        auth = tweepy.OAuthHandler(settings.TWITTER_CONSUMER_KEY,
                                   settings.TWITTER_CONSUMER_SECRET)
        auth.set_access_token(auth_token.access_token,
                              auth_token.access_token_secret)
        try:
            api = tweepy.API(auth, wait_on_rate_limit=True)
        except tweepy.TweepError:
            raise CommandError('Error! Failed to get access token for user %s.' % screen_name)
        for friend in tweepy.Cursor(api.friends).items():
            if not friend.url:
                continue
            timeline = friend.timeline()
            statuses = [status for status in timeline if status.author.screen_name == friend.screen_name]
            if statuses:
                last_updated = pytz.utc.localize(statuses[0].created_at)
            else:
                last_updated = pytz.utc.localize(datetime.datetime.now())
            twitter_account, created = TwitterAccount.objects.get_or_create(screen_name=friend.screen_name, defaults={'last_updated':last_updated})
            if created:
                twitter_account.save()
                twitter_account.followed_from.add(auth_token)
            else:
                if not twitter_account.followed_from.filter(uuid=auth_token.uuid).exists():
                    twitter_account.followed_from.add(auth_token)
                twitter_account.last_updated = last_updated
            twitter_account.save()
            for tweet in statuses:
                if pytz.utc.localize(tweet.created_at) > twitter_account.last_updated:
                    twitter_account.last_updated = pytz.utc.localize(tweet.created_at)
                if getattr(tweet, 'retweeted_status', None) and tweet.text.endswith(u'\u2026'):
                    text = twitter_account.screen_name + ' Retweeted ' + tweet.retweeted_status.author.screen_name + ': ' + tweet.retweeted_status.text
                else:
                    text = tweet.text
                tweeted_at = pytz.utc.localize(tweet.created_at)
                url = 'https://twitter.com/' + twitter_account.screen_name + '/status/' + tweet.id_str
                status_obj = TwitterStatus(
                    tweet_from=twitter_account,
                    followed_from=auth_token,
                    status_text=text,
                    status_url=url)
                status_obj.status_created=tweeted_at
                status_obj.save()

                if tweet._json['entities'].get('urls', []):
                    for url_entity in tweet._json['entities']['urls']:
                        if url_entity.get('expanded_url', ''):
                            shared_at = pytz.utc.localize(tweet.created_at)
                            link_obj, created = UrlShared.objects.get_or_create(
                                url=url_entity['expanded_url'],
                                defaults={'url_shared':pytz.utc.localize(tweet.created_at)})
                            if created:
                                link_obj.save()
                            if not link_obj.shared_from.filter(uuid=twitter_account.uuid).exists():
                                link_obj.shared_from.add(twitter_account)
                            link_obj.save()
            # rss_task.apply_async([friend.url, friend.screen_name, friend.name, friend.id_str, statuses])
