# Generated by Django 2.2.24 on 2022-01-21 13:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('form_processor', '0094_rename_xformoperation'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CommCareCaseSQL',
            new_name='CommCareCase',
        ),
    ]
