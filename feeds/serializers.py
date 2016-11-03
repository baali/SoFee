from rest_framework import serializers
from feeds.models import UrlShared, TwitterStatus, TwitterAccount


class TwitterAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwitterAccount
        fields = ('screen_name', )


class UrlSerializer(serializers.ModelSerializer):
    shared_from = TwitterAccountSerializer(many=True)

    class Meta:
        model = UrlShared
        fields = ('uuid', 'url', 'shared_from', 'url_shared', 'url_seen', 'quoted_text')


class StatusSerializer(serializers.ModelSerializer):
    tweet_from = TwitterAccountSerializer()

    class Meta:
        model = TwitterStatus
        fields = ('uuid', 'tweet_from', 'followed_from', 'status_text', 'status_created', 'status_seen', 'status_url')
