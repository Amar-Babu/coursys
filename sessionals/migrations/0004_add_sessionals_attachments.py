# Generated by Django 2.0.3 on 2018-09-21 11:41

import autoslug.fields
import django.core.files.storage
from django.db import migrations, models
import django.db.models.deletion
import sessionals.models


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0021_new_roles'),
        ('sessionals', '0003_on_delete'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionalAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250)),
                ('slug', autoslug.fields.AutoSlugField(editable=False, populate_from='title', unique_with=('sessional',))),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contents', models.FileField(max_length=500, storage=django.core.files.storage.FileSystemStorage(base_url=None, location='submitted_files'), upload_to=sessionals.models.sessional_attachment_upload_to)),
                ('mediatype', models.CharField(blank=True, editable=False, max_length=200, null=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('created_by', models.ForeignKey(help_text='Document attachment created by.', on_delete=django.db.models.deletion.PROTECT, to='coredata.Person')),
                ('sessional', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attachments', to='sessionals.SessionalContract')),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.AlterUniqueTogether(
            name='sessionalattachment',
            unique_together={('sessional', 'slug')},
        ),
    ]
