# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submission', '0002_autoslug'),
    ]

    operations = [
        migrations.CreateModel(
            name='GitTagComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent')),
                ('check', models.BooleanField(default=False, help_text=b'Check that the repository and tag really exists? Implies that all submitted repos must be public http:// or https:// URLs.')),
                ('prefix', models.CharField(help_text=b'Prefix that the URL *must* start with. (e.g. "git@github.com:" or "https://github.com", blank for none.)', max_length=200, null=True, blank=True)),
            ],
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedGitTag',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent')),
                ('url', models.CharField(help_text=b'Clone URL for your repository, like "https://server/user/repo.git" or "git@server:user/repo.git".', max_length=500, verbose_name=b'Repository URL')),
                ('tag', models.CharField(help_text=b'The tag you\'re submitting: created like "git tag submitted_code; git push origin --tags"', max_length=200, verbose_name=b'Tag name')),
                ('component', models.ForeignKey(to='submission.GitTagComponent')),
            ],
            bases=('submission.submittedcomponent',),
        ),
    ]
