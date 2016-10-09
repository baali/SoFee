from rest_framework import serializers
from feeds.models import UrlShared, TwitterStatus


class UrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = UrlShared
        fields = ('uuid', 'url', 'shared_from', 'url_shared', 'url_seen')


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwitterStatus
        fields = ('uuid', 'tweet_from', 'followed_from', 'status_text', 'status_created', 'status_seen', 'status_url')
