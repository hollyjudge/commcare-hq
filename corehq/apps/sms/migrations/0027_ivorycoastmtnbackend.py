# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-15 12:54
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sms', '0026_add_messagingsubevent_case_id_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='IvoryCoastMTNBackend',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('sms.sqlsmsbackend',),
        ),
    ]
