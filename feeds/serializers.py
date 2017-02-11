from rest_framework import serializers
from feeds.models import PushNotificationToken, TwitterAccount,\
    UrlShared, TwitterStatus


class SmallerSetJsonField(serializers.JSONField):
    """Class to expose Smaller set of JSON fields."""
    def to_representation(self, value):
        limited_dict = {}
        if 'profile_image_url_https' in value:
            limited_dict['profile_image_url'] = value['profile_image_url_https']
        limited_dict['url'] = 'https://twitter.com/' + value.get('screen_name', '')
        limited_dict['screen_name'] = value.get('screen_name', '')
        limited_dict['name'] = value.get('name', '')
        return limited_dict


class TwitterAccountSerializer(serializers.ModelSerializer):
    account_json = SmallerSetJsonField()

    class Meta:
        model = TwitterAccount
        fields = ('screen_name', 'account_json')


class UrlSerializer(serializers.ModelSerializer):
    shared_from = TwitterAccountSerializer(many=True)

    class Meta:
        model = UrlShared
        fields = ('uuid', 'url', 'shared_from', 'url_shared', 'url_seen', 'quoted_text', 'cleaned_text', 'url_json')


class StatusSerializer(serializers.ModelSerializer):
    tweet_from = TwitterAccountSerializer()

    class Meta:
        model = TwitterStatus
        fields = ('uuid', 'tweet_from', 'followed_from', 'status_text', 'status_created', 'status_seen', 'status_url')


class PushNotificationSerializer(serializers.ModelSerializer):
    token_for = TwitterAccountSerializer(read_only=True)

    class Meta:
        model = PushNotificationToken
        fields = ('token', 'token_for', 'active')
