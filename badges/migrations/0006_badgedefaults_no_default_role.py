# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-26 21:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('badges', '0005_auto_20160306_1426'),
    ]

    operations = [
        migrations.AddField(
            model_name='badgedefaults',
            name='no_default_role',
            field=models.BooleanField(default=False, verbose_name='Do not print default roles on badges'),
        ),
    ]
