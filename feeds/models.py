from __future__ import unicode_literals

from django.db import models
import uuid

# Create your models here.


class AuthToken(models.Model):
    uuid = models.CharField(max_length=64, default=uuid.uuid4,
                            db_index=True)
    screen_name = models.CharField(max_length=60, unique=True)
    # Should they be stored directly
    access_token = models.CharField(max_length=120)
    access_token_secret = models.CharField(max_length=120)


class TwitterAccount(models.Model):
    screen_name = models.CharField(max_length=60, unique=True)
    followed_from = models.ForeignKey(AuthToken, on_delete=models.CASCADE)
    last_updated = models.DateTimeField()

    def __str__(self):              # __unicode__ on Python 2
        return self.screen_name


class TwitterStatus(models.Model):
    tweet_from = models.ForeignKey(TwitterAccount, on_delete=models.CASCADE)
    followed_from = models.ForeignKey(AuthToken, on_delete=models.CASCADE)
    # Now links/urls are excluded from 140 character limit
    status_text = models.CharField(max_length=240, unique=True)
    status_created = models.DateTimeField()
    status_seen = models.BooleanField(default=False)

    def __str__(self):              # __unicode__ on Python 2
        return self.tweet_from, self.status_text
