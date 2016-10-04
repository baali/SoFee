from django.test import TestCase
import os
import tweepy
import pytz
# from django.contrib.staticfiles import finders
from django.test import Client
from django.core.urlresolvers import reverse
from feeds import models
import datetime
from rest_framework import status


class FeedsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        """
        cls.oauth_consumer_key = os.environ.get('CONSUMER_KEY', '')
        cls.oauth_consumer_secret = os.environ.get('CONSUMER_SECRET', '')
        cls.oauth_token = os.environ.get('ACCESS_KEY', '')
        cls.oauth_token_secret = os.environ.get('ACCESS_SECRET', '')
        cls.auth = tweepy.OAuthHandler(cls.oauth_consumer_key, cls.oauth_consumer_secret)
        cls.auth.set_access_token(cls.oauth_token, cls.oauth_token_secret)
        cls.api = tweepy.API(cls.auth, wait_on_rate_limit=True)
        cls.me = cls.api.me()
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=cls.me.screen_name)
        auth_token.access_token = cls.oauth_token
        auth_token.access_token_secret = cls.oauth_token_secret
        auth_token.save()
        friends_counter = 0
        for friend in tweepy.Cursor(cls.api.friends).items():
            if not friend.url:
                continue
            last_updated = pytz.utc.localize(datetime.datetime.now() - datetime.timedelta(days=365))
            twitter_account, created = models.TwitterAccount.objects.get_or_create(screen_name=friend.screen_name,
                                                                                   followed_from=auth_token)
            twitter_account.last_updated = last_updated
            twitter_account.save()
            statuses = cls.api.user_timeline(screen_name=friend.screen_name)
            for tweet in statuses:
                if pytz.utc.localize(tweet.created_at) > twitter_account.last_updated:
                    twitter_account.last_updated = pytz.utc.localize(tweet.created_at)
                if getattr(tweet, 'retweeted_status', None) and tweet.text.endswith(u'\u2026'):
                    text = twitter_account.screen_name + ' Retweeted ' + tweet.retweeted_status.author.screen_name + ': ' + tweet.retweeted_status.text
                else:
                    text = tweet.text
                created = pytz.utc.localize(tweet.created_at)
                url = 'https://twitter.com/' + twitter_account.screen_name + '/status/' + tweet.id_str
                status_obj = models.TwitterStatus.objects.create(
                    tweet_from=twitter_account,
                    followed_from=auth_token,
                    status_text=text,
                    status_created=created,
                    status_url=url)
                status_obj.save()

                if tweet._json['entities'].get('urls', []):
                    for url_entity in tweet._json['entities']['urls']:
                        if url_entity.get('expanded_url', ''):
                            created = pytz.utc.localize(tweet.created_at)
                            link_obj = models.TwitterLink.objects.create(
                                url=url_entity['expanded_url'],
                                shared_from=twitter_account,
                                url_shared=created)
                            link_obj.save()

            friends_counter += 1
            if friends_counter >= 2:
                break

    @classmethod
    def tearDownClass(cls):
        pass

    def SetUp(self):
        self.client = Client()

    def test_get_opml(self):
        """
        Tests to make sure we get OPML file for an account.
        """
        pass

    def test_get_xml(self):
        """
        Tests to make sure we are able to download xml file.
        """
        pass

    def test_xml_content(self):
        """Tweet something using tweepy and making sure tweet gets reflected
        in RSS file.

        """
        pass

    def test_tweet_link(self):
        """Tweet a link using tweepy and making sure content of link are
        included in feed.

        """
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=self.me.screen_name)
        url = reverse('links', kwargs={'uuid': auth_token.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), models.TwitterLink.objects.count())

    def test_consolidated_feed(self):
        """Tests to get consolidated feed of all users account it following.

        """
        # session = self.client.session
        # session['access_key_tw'] = self.oauth_token
        # session['access_secret_tw'] = self.oauth_token_secret
        # session.save()
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=self.me.screen_name)
        url = reverse('statuses', kwargs={'uuid': auth_token.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), models.TwitterStatus.objects.filter(followed_from__uuid=auth_token.uuid).count())

    def test_archived_links(self):
        """Tests to make sure links shared on timeline are getting archived.
        # WHAT ABOUT - articles behind paywall/logins

        """
        pass

    def test_fetch_deleted_account(self):
        """Tests to make sure task to fetch statuses works fine in case
account is deleted/removed.

        """
        pass
