from django.test import TestCase
import os
import tweepy
import pytz
from django.contrib.staticfiles import finders
from django.test import Client
from django.core.urlresolvers import reverse
from feeds import models
import datetime
from rest_framework import status
from uuid import uuid4
from django.utils import timezone


class FeedsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        """
        cls.oauth_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', '')
        cls.oauth_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET', '')
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
        self_account, created = models.TwitterAccount.objects.get_or_create(screen_name=cls.me.screen_name)
        if created:
            self_account.save()
        self_account.followed_from.add(auth_token)
        last_updated = pytz.utc.localize(datetime.datetime.now() - datetime.timedelta(days=365))
        self_account.last_updated = last_updated
        self_account.save()

        friends_counter = 0
        for friend in tweepy.Cursor(cls.api.friends).items():
            if not friend.url:
                continue
            twitter_account, created = models.TwitterAccount.objects.get_or_create(screen_name=friend.screen_name)
            if created:
                twitter_account.save()
            twitter_account.followed_from.add(auth_token)
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
                created_at = pytz.utc.localize(tweet.created_at)
                url = 'https://twitter.com/' + twitter_account.screen_name + '/status/' + tweet.id_str
                status_obj = models.TwitterStatus(
                    tweet_from=twitter_account,
                    followed_from=auth_token,
                    status_text=text,
                    status_created=created_at,
                    status_url=url)
                status_obj.save()

                if tweet._json['entities'].get('urls', []):
                    for url_entity in tweet._json['entities']['urls']:
                        if url_entity.get('expanded_url', ''):
                            link_obj, created = models.UrlShared.objects.get_or_create(
                                url=url_entity['expanded_url'], defaults={'url_shared': pytz.utc.localize(tweet.created_at)})
                            if created:
                                link_obj.save()
                            if not link_obj.shared_from.filter(uuid=twitter_account.uuid).exists():
                                link_obj.shared_from.add(twitter_account)
                                link_obj.save()

            friends_counter += 1
            if friends_counter >= 3:
                break

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.client = Client()

    def test_get_opml(self):
        """
        Tests to make sure we get OPML file for an account.
        """
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=self.me.screen_name)
        url = reverse('opml', kwargs={'uuid': auth_token.uuid})
        # When: we pass feed parameter for user
        response = self.client.get(url)
        # Then: We are returned XML created from tweets
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(finders.find('opml/%s.opml' % auth_token.uuid))

    def test_get_feed_xml(self):
        """
        Tests to make sure we are able to download xml file.
        Enabling this for just Links at the moment.
        """
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=self.me.screen_name)
        url = reverse('links', kwargs={'uuid': auth_token.uuid})
        # When: we pass feed parameter for user
        response = self.client.get(url, data={'feed': '1'})
        # Then: We are returned XML created from tweets
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(finders.find('xml/%s-feed.xml' % auth_token.uuid))

    def test_get_feed_xml_dates(self):
        """Tests to make sure we are able to query system for feeds of
        different dates, default being today.

        """
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=self.me.screen_name)
        url = reverse('links', kwargs={'uuid': auth_token.uuid})
        # When: we pass no data parameter, today's feed is returned
        response = self.client.get(url, data={'feed': '1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(finders.find('xml/%s-feed.xml' % auth_token.uuid))
        # Then: date returned in response is of today
        self.assertEqual(response.data['date'], datetime.date.today().strftime('%d %b %Y'))

        # Do: get random date from record
        random_date = models.UrlShared.objects.all().datetimes('url_shared', 'day').order_by('?').first().strftime('%d %b %Y')
        # When: We pass this date as one of query parameter
        response = self.client.get(url, data={'feed': '1', 'date': random_date})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(finders.find('xml/%s-feed.xml' % auth_token.uuid))
        # Then: date returned in response is same as the one passed as query parameter
        self.assertEqual(response.data['date'], random_date)

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
        time_threshold = timezone.now() - datetime.timedelta(hours=24)
        self.assertEqual(len(response.data), models.UrlShared.objects.filter(url_shared__gte=time_threshold).count())
        # When: we use random UUID and query for links
        url = reverse('links', kwargs={'uuid': str(uuid4())})
        response = self.client.get(url)
        # Then: we get 404, NotFound response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tweet_links_post(self):
        """Tests to post link and store it.

        """
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=self.me.screen_name)
        url = reverse('links', kwargs={'uuid': auth_token.uuid})
        # When: We make request with url to be stored
        response = self.client.post(url, data={'url_shared': 'http://journal.burningman.org/2016/10/philosophical-center/tenprinciples/a-brief-history-of-who-ruined-burning-man/'}, format='json')
        # Then: we get 201, Created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # When: We query for links shared by this user.
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Then: The url we just posted should also be returned in list
        self.assertIn('http://journal.burningman.org/2016/10/philosophical-center/tenprinciples/a-brief-history-of-who-ruined-burning-man/',
                      [shared_url['url'] for shared_url in response.data])
        # When: We post a url with all query parameters.
        response = self.client.post(url, data={'url_shared': 'http://www.nytimes.com/2016/09/03/your-money/caregivers-alzheimers-burnout.html?smid=tw-nythealth&smtyp=cur'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(url)
        # Then: Only base URL without query string should be part of URL sahred
        self.assertIn('http://www.nytimes.com/2016/09/03/your-money/caregivers-alzheimers-burnout.html',
                      [shared_url['url'] for shared_url in response.data])
        # Then: Also make sure that url with query-params is not there.
        self.assertNotIn('http://www.nytimes.com/2016/09/03/your-money/caregivers-alzheimers-burnout.html?smid=tw-nythealth&smtyp=cur',
                         [shared_url['url'] for shared_url in response.data])

        # When: We post a url with all query parameters.
        response = self.client.post(url, data={'url_shared': 'http://www.politico.com/story/2016/10/donald-trump-gop-ticket-229339#ixzz4MUelDXDC'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(url)
        # Then: Only base URL without query string should be part of URL sahred
        self.assertIn('http://www.politico.com/story/2016/10/donald-trump-gop-ticket-229339',
                      [shared_url['url'] for shared_url in response.data])
        # Then: Also make sure that url with query-params is not there.
        self.assertNotIn('http://www.politico.com/story/2016/10/donald-trump-gop-ticket-229339#ixzz4MUelDXDC',
                         [shared_url['url'] for shared_url in response.data])

    def test_tweet_links_individual(self):
        """Tests to confirm that fetching links shared by single account
works.

        """
        auth_token, created = models.AuthToken.objects.get_or_create(screen_name=self.me.screen_name)
        url = reverse('links', kwargs={'uuid': auth_token.uuid})
        # Do: Get a random UUID existing in records
        random_existing_uuid = models.TwitterAccount.objects.all().order_by('?').first().uuid
        # When: We make request with parameter 'links_of'
        response = self.client.get(url, data={'links_of': random_existing_uuid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        time_threshold = timezone.now() - datetime.timedelta(hours=24)
        self.assertEqual(len(response.data), models.UrlShared.objects.filter(shared_from__uuid=random_existing_uuid, url_shared__gte=time_threshold).count())
        # When: we use random UUID and query for links
        response = self.client.get(url, data={'links_of': str(uuid4())})
        # Then: we get 404, NotFound response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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
        time_threshold = timezone.now() - datetime.timedelta(hours=24)
        self.assertEqual(len(response.data['results']), models.TwitterStatus.objects.filter(followed_from__uuid=auth_token.uuid, status_created__gte=time_threshold).count())

        # When: we use random UUID and query for links
        url = reverse('links', kwargs={'uuid': str(uuid4())})
        response = self.client.get(url)
        # Then: we get 404, NotFound response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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
