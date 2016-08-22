from __future__ import unicode_literals

from django.db import models

# Create your models here.

class AuthTokens(models.Model):
    screen_name = models.CharField(max_length=60, unique=True)
    access_token = models.CharField(max_length=120)
    access_token_secret = models.CharField(max_length=120)

class TwitterAccounts(models.Model):
    screen_name = models.CharField(max_length=60, unique=True)
    followed_from = models.ForeignKey(AuthTokens, on_delete=models.CASCADE)
    last_updated = models.DateTimeField()
    def __str__(self):              # __unicode__ on Python 2
        return self.screen_name
