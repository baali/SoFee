# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-11-22 04:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='urlshared',
            name='cleaned_text',
            field=models.TextField(blank=True),
        ),
    ]
