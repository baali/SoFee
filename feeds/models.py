from __future__ import unicode_literals

from django.db import models

# Create your models here.

class AuthTokens(models.Model):
    screen_name = models.CharField(max_length=60, unique=True)
    access_token = models.CharField(max_length=120)
    access_token_secret = models.CharField(max_length=120)
