import uuid
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.sites.shortcuts import get_current_site

class UUIDMixin(models.Model):
    
    uuid = models.CharField(max_length=64, default=uuid.uuid4,
                            db_index=True, primary_key=True, editable=False)

    class Meta(object):
        abstract = True

    def generate_uuid(self):
        try:
            if not self.uuid and self.pk:
                self.uuid = uuid.uuid5(uuid.NAMESPACE_URL, self.get_uuid_url())
        except (AttributeError, ValueError) as e:
            pass
        return self.uuid

    def get_uuid_url(self, request=None):
        if not self.pk:
            return None
        ct=ContentType.objects.get_for_model(self)
        return "http://{0}/{1}/{2}/".format(get_current_site(request).domain,
                                            ct.model, self.pk)
