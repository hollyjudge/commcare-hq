# Generated by Django 3.2.13 on 2022-07-27 14:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0008_tableauvisualization_title'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tableauserver',
            name='domain_username',
        ),
    ]