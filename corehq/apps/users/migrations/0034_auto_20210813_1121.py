# Generated by Django 2.2.24 on 2021-08-13 11:21

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0033_rename_sqluserrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='userhistory',
            name='change_messages',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='userhistory',
            name='changed_via',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='userhistory',
            name='changes',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
    ]