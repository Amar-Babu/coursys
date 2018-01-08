# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2018-01-02 16:29
from __future__ import unicode_literals

from django.db import migrations

DATABASE_QUERY_TEMPLATE = "ALTER DATABASE %s CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;"
TABLE_QUERY_TEMPLATE = "ALTER TABLE %s CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"


def forwards_func(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        # this only makes sense on mysql where Unicode handling is more... amusing.
        return

    schema_editor.connection.disable_constraint_checking()

    tables = schema_editor.connection.introspection.table_names()
    for t in tables:
        if t in ['celery_taskmeta', 'celery_tasksetmeta', 'django_celery_beat_periodictask', 'djcelery_periodictask',
                 'djcelery_taskstate', 'djcelery_workerstate', 'djkombu_queue']:
            continue
        print('Altering %s' % (t,))
        query = TABLE_QUERY_TEMPLATE % (t,)
        schema_editor.execute(query)

    schema_editor.connection.enable_constraint_checking()

    db_name = schema_editor.connection.settings_dict['NAME']
    schema_editor.execute(DATABASE_QUERY_TEMPLATE % (db_name,))


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0018_add_course_descriptions'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
