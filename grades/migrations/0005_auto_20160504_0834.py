# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-04 08:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0004_comment_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calletteractivity',
            name='exam_activity',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='exam_letter_activity', to='grades.Activity'),
        ),
    ]
