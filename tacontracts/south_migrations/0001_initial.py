# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'HiringSemester'
        db.create_table(u'tacontracts_hiringsemester', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('deadline_for_acceptance', self.gf('django.db.models.fields.DateField')()),
            ('pay_start', self.gf('django.db.models.fields.DateField')()),
            ('pay_end', self.gf('django.db.models.fields.DateField')()),
            ('payperiods', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('config', self.gf('courselib.json_fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'tacontracts', ['HiringSemester'])

        # Adding unique constraint on 'HiringSemester', fields ['semester', 'unit']
        db.create_unique(u'tacontracts_hiringsemester', ['semester_id', 'unit_id'])

        # Adding model 'TACategory'
        db.create_table(u'tacontracts_tacategory', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ra.Account'])),
            ('hiring_semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tacontracts.HiringSemester'])),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('pay_per_bu', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('scholarship_per_bu', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('bu_lab_bonus', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2014, 8, 8, 0, 0))),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('config', self.gf('courselib.json_fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'tacontracts', ['TACategory'])

        # Adding model 'TAContract'
        db.create_table(u'tacontracts_tacontract', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contract', to=orm['tacontracts.TACategory'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='NEW', max_length=4)),
            ('sin', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('deadline_for_acceptance', self.gf('django.db.models.fields.DateField')()),
            ('pay_start', self.gf('django.db.models.fields.DateField')()),
            ('pay_end', self.gf('django.db.models.fields.DateField')()),
            ('payperiods', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('appointment', self.gf('django.db.models.fields.CharField')(default='INIT', max_length=4)),
            ('conditional_appointment', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('tssu_appointment', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('accepted_by_student', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('comments', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('config', self.gf('courselib.json_fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'tacontracts', ['TAContract'])

        # Adding model 'TACourse'
        db.create_table(u'tacontracts_tacourse', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['coredata.CourseOffering'])),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(related_name='course', to=orm['tacontracts.TAContract'])),
            ('bu', self.gf('django.db.models.fields.DecimalField')(max_digits=4, decimal_places=2)),
            ('labtut', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None)),
            ('config', self.gf('courselib.json_fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'tacontracts', ['TACourse'])

        # Adding unique constraint on 'TACourse', fields ['contract', 'course']
        db.create_unique(u'tacontracts_tacourse', ['contract_id', 'course_id'])

        # Adding model 'EmailReceipt'
        db.create_table(u'tacontracts_emailreceipt', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(related_name='email_receipt', to=orm['tacontracts.TAContract'])),
            ('content', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dashboard.NewsItem'])),
        ))
        db.send_create_signal(u'tacontracts', ['EmailReceipt'])


    def backwards(self, orm):
        # Removing unique constraint on 'TACourse', fields ['contract', 'course']
        db.delete_unique(u'tacontracts_tacourse', ['contract_id', 'course_id'])

        # Removing unique constraint on 'HiringSemester', fields ['semester', 'unit']
        db.delete_unique(u'tacontracts_hiringsemester', ['semester_id', 'unit_id'])

        # Deleting model 'HiringSemester'
        db.delete_table(u'tacontracts_hiringsemester')

        # Deleting model 'TACategory'
        db.delete_table(u'tacontracts_tacategory')

        # Deleting model 'TAContract'
        db.delete_table(u'tacontracts_tacontract')

        # Deleting model 'TACourse'
        db.delete_table(u'tacontracts_tacourse')

        # Deleting model 'EmailReceipt'
        db.delete_table(u'tacontracts_emailreceipt')


    models = {
        u'coredata.course': {
            'Meta': {'ordering': "('subject', 'number')", 'unique_together': "(('subject', 'number'),)", 'object_name': 'Course'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        u'coredata.courseoffering': {
            'Meta': {'ordering': "['-semester', 'subject', 'number', 'section']", 'unique_together': "(('semester', 'subject', 'number', 'section'), ('semester', 'crse_id', 'section'), ('semester', 'class_nbr'))", 'object_name': 'CourseOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'class_nbr': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '3', 'db_index': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Course']"}),
            'crse_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'enrl_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instr_mode': ('django.db.models.fields.CharField', [], {'default': "'P'", 'max_length': '2', 'db_index': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'symmetrical': 'False', 'through': u"orm['coredata.Member']", 'to': u"orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']", 'null': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'units': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        u'coredata.member': {
            'Meta': {'ordering': "['offering', 'person']", 'object_name': 'Member'},
            'added_reason': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'career': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'credits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labtut_section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.CourseOffering']"}),
            'official_grade': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'person'", 'to': u"orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        u'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'coredata.semester': {
            'Meta': {'ordering': "['name']", 'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        u'coredata.unit': {
            'Meta': {'ordering': "['label']", 'object_name': 'Unit'},
            'acad_org': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        u'dashboard.newsitem': {
            'Meta': {'object_name': 'NewsItem'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'author'", 'null': 'True', 'to': u"orm['coredata.Person']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.CourseOffering']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'published': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'source_app': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'user'", 'to': u"orm['coredata.Person']"})
        },
        u'ra.account': {
            'Meta': {'ordering': "['account_number']", 'object_name': 'Account'},
            'account_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'tacontracts.emailreceipt': {
            'Meta': {'object_name': 'EmailReceipt'},
            'content': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dashboard.NewsItem']"}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'email_receipt'", 'to': u"orm['tacontracts.TAContract']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'tacontracts.hiringsemester': {
            'Meta': {'unique_together': "(('semester', 'unit'),)", 'object_name': 'HiringSemester'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'deadline_for_acceptance': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pay_end': ('django.db.models.fields.DateField', [], {}),
            'pay_start': ('django.db.models.fields.DateField', [], {}),
            'payperiods': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Semester']"}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'tacontracts.tacategory': {
            'Meta': {'object_name': 'TACategory'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ra.Account']"}),
            'bu_lab_bonus': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2014, 8, 8, 0, 0)'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hiring_semester': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tacontracts.HiringSemester']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pay_per_bu': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'scholarship_per_bu': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'tacontracts.tacontract': {
            'Meta': {'object_name': 'TAContract'},
            'accepted_by_student': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'appointment': ('django.db.models.fields.CharField', [], {'default': "'INIT'", 'max_length': '4'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contract'", 'to': u"orm['tacontracts.TACategory']"}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'conditional_appointment': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'deadline_for_acceptance': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pay_end': ('django.db.models.fields.DateField', [], {}),
            'pay_start': ('django.db.models.fields.DateField', [], {}),
            'payperiods': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"}),
            'sin': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '4'}),
            'tssu_appointment': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'tacontracts.tacourse': {
            'Meta': {'unique_together': "(('contract', 'course'),)", 'object_name': 'TACourse'},
            'bu': ('django.db.models.fields.DecimalField', [], {'max_digits': '4', 'decimal_places': '2'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'course'", 'to': u"orm['tacontracts.TAContract']"}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.CourseOffering']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labtut': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'})
        }
    }

    complete_apps = ['tacontracts']