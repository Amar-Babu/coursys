import os
from django.db import models, transaction
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
from coredata.models import Person, Unit
from jsonfield import JSONField
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from courselib.json_fields import getter_setter
from django.db.models import Max
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.conf import settings
from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
import datetime, random, sha, itertools

# choices for Form.initiator field
from onlineforms.fieldtypes.other import FileCustomField, DividerField, URLCustomField, ListField, SemesterField, DateSelectField
from onlineforms.fieldtypes.select import DropdownSelectField, RadioSelectField, MultipleSelectField
from onlineforms.fieldtypes.text import SmallTextField, MediumTextField, LargeTextField, ExplanationTextField, EmailTextField

INITIATOR_CHOICES = [
        ('LOG', 'Logged-in SFU users'),
        ('ANY', 'Anyone, including non-SFU users'),
        ('NON', 'Nobody: form cannot be filled out'),  # used to deactivate a form, or during creation/editing.
        # may add others if needed, e.g. instructors, admin staff, majors in a specific program, ...
        ]
INITIATOR_SHORT = {
        'LOG': 'SFU Users',
        'ANY': 'Anyone (including non-SFU)',
        'NON': 'Nobody (form disabled)',
        }

# choices for the Sheet.can_view field
VIEWABLE_CHOICES = [
        ('ALL', 'Filler can see all info on previous sheets'),
        ('NON', "Filler can't see any info on other sheets (just name/email of initiator)"),
        ]
VIEWABLE_SHORT = {
        'ALL': 'Can see info on previous sheets',
        'NON': 'Can only see name/email',
        }

# choices for the Field.fieldtype field
FIELD_TYPE_CHOICES = [
        ('SMTX', 'Small Text (single line)'),
        ('MDTX', 'Medium Text (a few lines)'),
        ('LGTX', 'Large Text (many lines)'),
        ('EMAI', 'Email address'),
        ('RADI', 'Select with radio buttons'),
        ('SEL1', 'Select with a drop-down menu'),
        ('SELN', 'Select multiple values'),
        ('LIST', 'Enter a list of short responses'),
        ('FILE', 'Upload a file'),
        ('URL', 'Web page address (URL)'),
        ('TEXT', 'Explanation block (user enters nothing)'),
        ('DIVI', 'Divider'),
        ('DATE', 'A date'),
        ('SEM', 'Semester'),
        # more may be added.
        ]
FIELD_TYPES = dict(FIELD_TYPE_CHOICES)

# mapping of field types to FieldType objects that implement their logic
#from onlineforms.fieldtypes import *
FIELD_TYPE_MODELS = {
        'SMTX': SmallTextField,
        'MDTX': MediumTextField,
        'LGTX': LargeTextField,
        'EMAI': EmailTextField,
        'RADI': RadioSelectField,
        'SEL1': DropdownSelectField,
        'SELN': MultipleSelectField,
        'LIST': ListField,
        'FILE': FileCustomField,
        'URL': URLCustomField,
        'TEXT': ExplanationTextField,
        'DIVI': DividerField,
        'DATE': DateSelectField,
        'SEM': SemesterField,
        }

# mapping of different statuses the forms can be in
SUBMISSION_STATUS = [
        ('WAIT', "Waiting for the owner to send it to someone else or change status to \"done\""),
        ('DONE', "No further action required"),
        ('REJE', "Returned incomplete"),
        ]
        
FORM_SUBMISSION_STATUS = [
        ('PEND', "The document is still being worked on"),
        ] + SUBMISSION_STATUS

class NonSFUFormFiller(models.Model):
    """
    A person without an SFU account that can fill out forms.
    """
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    email_address = models.EmailField(max_length=254)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    def __unicode__(self):
        return "%s, %s" % (self.last_name, self.first_name)
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)
    def sortname(self):
        return "%s, %s" % (self.last_name, self.first_name)
    def initials(self):
        return "%s%s" % (self.first_name[0], self.last_name[0])
    def full_email(self):
        return "%s <%s>" % (self.name(), self.email())
    def email(self):
        return self.email_address

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    
    def email_mailto(self):
        "A mailto: URL for this person's email address: handles the case where we don't know an email for them."
        email = self.email()
        if email:
            return mark_safe('<a href="mailto:%s">%s</a>' % (escape(email), escape(email)))
        else:
            return "None"

class FormFiller(models.Model):
    """
    A wrapper class for filling forms. Is either a SFU account(Person) or a nonSFUFormFiller.
    """
    sfuFormFiller = models.ForeignKey(Person, null=True)
    nonSFUFormFiller = models.ForeignKey(NonSFUFormFiller, null=True)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    def getFormFiller(self):
        if self.sfuFormFiller:
            return self.sfuFormFiller
        elif self.nonSFUFormFiller:
            return self.nonSFUFormFiller
        else:
            raise Exception, "This form filler object is in an invalid state."

    def isSFUPerson(self):
        return bool(self.sfuFormFiller)

    def __unicode__(self):
        if self.sfuFormFiller:
            return "%s (%s)" % (self.sfuFormFiller.name(), self.sfuFormFiller.emplid)
        else:
            return "%s (external user)" % (self.nonSFUFormFiller.name(),)
    def name(self):
        formFiller = self.getFormFiller()
        return formFiller.name()
    def sortname(self):
        formFiller = self.getFormFiller()
        return formFiller.sortname()
    def initials(self):
        formFiller = self.getFormFiller()
        return formFiller.initials()
    def full_email(self):
        formFiller = self.getFormFiller()
        return formFiller.full_email()
    def email(self):
        formFiller = self.getFormFiller()
        return formFiller.email()
    def identifier(self):
        """
        Identifying string that can be used for slugs
        """
        if self.sfuFormFiller:
            return self.sfuFormFiller.userid_or_emplid()
        else:
            return self.nonSFUFormFiller.email() \
                   .replace('@', '-').replace('.', '-')

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    
    def email_mailto(self):
        formFiller = self.getFormFiller()
        return formFiller.email_mailto()

class FormGroup(models.Model):
    """
    A group that owns forms and form submissions.
    """
    unit = models.ForeignKey(Unit)
    name = models.CharField(max_length=60, null=False, blank=False)
    members = models.ManyToManyField(Person, through='FormGroupMember') #
    def autoslug(self):
        return make_slug(self.unit.label + ' ' + self.name)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    class Meta:
        unique_together = (("unit", "name"),)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.unit.label)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."

class FormGroupMember(models.Model):
    """
    Member of a FormGroup. Upgraded for simple ManyToManyField so we have the .config

    Do not use as a foreign key: is deleted when people leave the FormGroup
    """
    person = models.ForeignKey(Person)
    formgroup = models.ForeignKey(FormGroup)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:
        # 'email': should this member receive emails on completed sheets?

    defaults = {'email': True}
    email, set_email = getter_setter('email')

    class Meta:
        db_table = 'onlineforms_formgroup_members' # to make it Just Work with the FormGroup.members without "through=" that existed previously
        unique_together = (("person", "formgroup"),)

    def __unicode__(self):
        return "%s in %s" % (self.person.name(), self.formgroup.name)


class _FormCoherenceMixin(object):
    """
    Class to mix-in to maintain the .active and .original fields
    properly when saving form objects.
    """
    def clone(self):
        """
        Return a cloned copy of self, which has *not* been saved.
        """
        # from http://stackoverflow.com/a/4733702
        new_kwargs = dict([(fld.name, getattr(self, fld.name)) 
                           for fld in self._meta.fields if fld.name != self._meta.pk.name])
        return self.__class__(**new_kwargs)

    def cleanup_fields(self):
        """
        Called after self.save() to manage the .active and .original fields
        """
        # There can be only one [active instance of this Form/Sheet/Field].
        if self.active and self.original:
            others = type(self).objects.filter(original=self.original) \
                                 .exclude(id=self.id)
            
            # only de-activate siblings, not cousins.
            # i.e. other related sheets/fields in *other* versions of the form should still be active
            if isinstance(self, Sheet):
                others = others.filter(form=self.form)
            elif isinstance(self, Field):
                others = others.filter(sheet=self.sheet)
            
            others.update(active=False)

        # ensure self.original is populated: should already be set to
        # oldinstance.original when copying.
        if not self.original:
            assert self.id # infinite loop if called before self is saved (and thus gets an id)
            self.original = self
            self.save()


class Form(models.Model, _FormCoherenceMixin):
    title = models.CharField(max_length=60, null=False, blank=False, help_text='The name of this form.')
    owner = models.ForeignKey(FormGroup, help_text='The group of users who own/administrate this form.')
    description = models.CharField(max_length=500, null=False, blank=False, help_text='A brief description of the form that can be displayed to users.')
    initiators = models.CharField(max_length=3, choices=INITIATOR_CHOICES, default="NON", help_text='Who is allowed to fill out the initial sheet? That is, who can initiate a new instance of this form?')
    unit = models.ForeignKey(Unit)
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    advisor_visible = models.BooleanField(default=False, help_text="Should submissions be visible to advisors in this unit?")
    def autoslug(self):
        return make_slug(self.unit.label + ' ' + self.title)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    def __unicode__(self):
        return "%s [%s]" % (self.title, self.id)
    
    def delete(self, *args, **kwargs):
        self.active = False
        self.save()

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        instance = super(Form, self).save(*args, **kwargs)
        self.cleanup_fields()
        return instance
    
    @property
    def initial_sheet(self):
        sheets = Sheet.objects.filter(form=self, active=True, is_initial=True)
        if len(sheets) > 0:
            return sheets[0]
        else:
            return None

    cached_sheets = None
    def get_sheets(self, refetch=False):
        if refetch or not(self.cached_sheets):
            self.cached_sheets = Sheet.objects.filter(form=self, active=True).order_by('order')
        return self.cached_sheets
    sheets = property(get_sheets)

    def get_initiators_display_short(self):
        return INITIATOR_SHORT[self.initiators]

class Sheet(models.Model, _FormCoherenceMixin):
    title = models.CharField(max_length=60, null=False, blank=False)
    # the form this sheet is a part of
    form = models.ForeignKey(Form)
    # specifies the order within a form
    order = models.PositiveIntegerField()
    # Flag to indicate whether this is the first sheet in the form
    is_initial = models.BooleanField(default=False)
    # indicates whether a person filling a sheet can see the results from all the previous sheets
    can_view = models.CharField(max_length=4, choices=VIEWABLE_CHOICES, default="NON", help_text='When someone is filling out this sheet, what else can they see?')
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:
    
    def autoslug(self):
        return make_slug(self.title)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='form')

    #class Meta:
    #    unique_together = (('form', 'order'),)

    def __unicode__(self):
        return "%s, %s [%i]" % (self.form, self.title, self.id)

    def delete(self, *args, **kwargs):
        if self.is_initial == True:
            raise NotImplementedError
        else:
            self.active = False
            self.save()

    class Meta:
        unique_together = (("form", "slug"),)
        ordering = ('order',)

    @transaction.commit_on_success
    def safe_save(self):
        """
        Save a copy of this sheet, and return the copy: does not modify self.
        """
        # clone the sheet
        sheet2 = self.clone()
        self.slug = self.slug + "_" + str(self.id)
        self.save()
        sheet2.save()
        sheet2.cleanup_fields()
        # copy the fields
        for field1 in Field.objects.filter(sheet=self, active=True):
            field2 = field1.clone()
            field2.sheet = sheet2
            field2.save()
        return sheet2       

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        # if this sheet is just being created it needs a order number
        if(self.order == None):
            max_aggregate = Sheet.objects.filter(form=self.form).aggregate(Max('order'))
            if(max_aggregate['order__max'] == None):
                next_order = 0
                # making first sheet for form--- initial 
                self.is_initial = True
            else:
                next_order = max_aggregate['order__max'] + 1
            self.order = next_order

        #assert (self.is_initial and self.order==0) or (not self.is_initial and self.order>0)
  
        super(Sheet, self).save(*args, **kwargs)
        self.cleanup_fields()

    cached_fields = None
    def get_fields(self, refetch=False):
        if refetch or not(self.cached_fields):
            self.cached_fields = Field.objects.filter(sheet=self, active=True).order_by('order')
        return self.cached_fields
    fields = property(get_fields)
    
    def get_can_view_display_short(self):
        return VIEWABLE_SHORT[self.can_view]

class Field(models.Model, _FormCoherenceMixin):
    label = models.CharField(max_length=60, null=False, blank=False)
    # the sheet this field is a part of
    sheet = models.ForeignKey(Sheet)
    # specifies the order within a sheet
    order = models.PositiveIntegerField()
    fieldtype = models.CharField(max_length=4, choices=FIELD_TYPE_CHOICES, default="SMTX")
    config = JSONField(null=False, blank=False, default={}) # configuration as required by the fieldtype. Must include 'required'
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def autoslug(self):
        return make_slug(self.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='sheet')

    def __unicode__(self):
        return "%s, %s" % (self.sheet, self.label)

    def delete(self, *args, **kwargs):
        self.active = False
        self.save()

    class Meta:
        unique_together = (("sheet", "slug"),)

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        # if this field is just being created it needs a order number
        if(self.order == None):
            max_aggregate = Field.objects.filter(sheet=self.sheet).aggregate(Max('order'))
            if(max_aggregate['order__max'] == None):
                next_order = 0
            else:
                next_order = max_aggregate['order__max'] + 1
            self.order = next_order


        super(Field, self).save(*args, **kwargs)
        self.cleanup_fields()

def neaten_field_positions(sheet):
    """
    update all positions to consecutive integers: seems possible to get identical positions in some cases
    """
    count = 1
    for f in Field.objects.filter(sheet=sheet, active=True).order_by('order'):
        f.position = count
        f.save()
        count += 1

class FormSubmission(models.Model):
    form = models.ForeignKey(Form)
    initiator = models.ForeignKey(FormFiller)
    owner = models.ForeignKey(FormGroup)
    status = models.CharField(max_length=4, choices=FORM_SUBMISSION_STATUS, default="PEND")
    def autoslug(self):
        return self.initiator.identifier()
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='form')
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:
        # 'summary': summary of the form entered when closing it
        # 'emailed': True if the initiator was emailed when the form was closed
        # 'closer': coredata.Person.id of the person that marked the formsub as DONE

    defaults = {'summary': '', 'emailed': False, 'closer': None}
    summary, set_summary = getter_setter('summary')
    emailed, set_emailed = getter_setter('emailed')
    closer_id, set_closer = getter_setter('closer')

    def update_status(self):
        sheet_submissions = SheetSubmission.objects.filter(form_submission=self) 
        if all(sheet_sub.status in ['DONE', 'REJE'] for sheet_sub in sheet_submissions):
            self.status = 'PEND'
        else:
            self.status = 'WAIT'
        self.save()

    def __unicode__(self):
        return "%s for %s" % (self.form, self.initiator)

    def closer(self):
        try:
            return Person.objects.get(id=self.closer_id())
        except Person.DoesNotExist:
            return None
    
    def last_sheet_completion(self):
        return self.sheetsubmission_set.all().aggregate(Max('completed_at'))['completed_at__max']

    def email_notify_completed(self, request, admin):
        plaintext = get_template('onlineforms/emails/notify_completed.txt')
        html = get_template('onlineforms/emails/notify_completed.html')

        email_context = Context({'formsub': self, 'admin': admin})
        subject = '%s submission complete' % (self.form.title)
        from_email = admin.full_email()
        to = self.initiator.full_email()
        msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                                     from_email=from_email, to=[to], bcc=[admin.full_email()])
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()

    def email_notify_new_owner(self, request, admin):
        plaintext = get_template('onlineforms/emails/notify_new_owner.txt')
        html = get_template('onlineforms/emails/notify_new_owner.html')

        full_url = request.build_absolute_uri(reverse('onlineforms.views.view_submission',
                                    kwargs={'form_slug': self.form.slug,
                                            'formsubmit_slug': self.slug}))
        email_context = Context({'formsub': self, 'admin': admin, 'adminurl': full_url})
        subject = '%s submission transferred' % (self.form.title)
        from_email = admin.full_email()
        to = [m.person.full_email()
              for m
              in self.owner.formgroupmember_set.all()
              if m.email()]
        msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                                     from_email=from_email, to=to, bcc=[admin.full_email()])
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()


class SheetSubmission(models.Model):
    form_submission = models.ForeignKey(FormSubmission)
    sheet = models.ForeignKey(Sheet)
    filler = models.ForeignKey(FormFiller)
    status = models.CharField(max_length=4, choices=SUBMISSION_STATUS, default="WAIT")
    given_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    # key = models.CharField()
    def autoslug(self):
        return self.filler.identifier()
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='form_submission')
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:
        # 'assign_note': optional note provided when sheet was assigned by admin
        # 'reject_reason': reason given for rejecting the sheet
        # 'return_reason': reason given for returning the sheet to the filler

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        self.completed_at = datetime.datetime.now()
        super(SheetSubmission, self).save(*args, **kwargs)
        self.form_submission.update_status()

    def __unicode__(self):
        return "%s by %s" % (self.sheet, self.filler.identifier())
    
    defaults = {'assign_note': None, 'reject_reason': None, 'return_reason': None}
    assign_note, set_assign_note = getter_setter('assign_note')
    reject_reason, set_reject_reason = getter_setter('reject_reason')
    return_reason, set_return_reason = getter_setter('return_reason')

    cached_fields = None
    def get_field_submissions(self, refetch=False):
        if refetch or not(self.cached_fields):
            self.cached_fields = FieldSubmission.objects.filter(sheet_submission=self)
        return self.cached_fields
    field_submissions = property(get_field_submissions)
    
    def get_secret(self):
        try:
            return SheetSubmissionSecretUrl.objects.get(sheet_submission=self)
        except SheetSubmissionSecretUrl.DoesNotExist:
            return None

    def get_submission_url(self):
        """
        Creates a URL for a sheet submission.
        If a secret URL has been generated it will use that,
        otherwise it will create a standard URL.
        """
        secret_urls = SheetSubmissionSecretUrl.objects.filter(sheet_submission=self)
        if secret_urls:
            return reverse('onlineforms.views.sheet_submission_via_url', kwargs={'secret_url': secret_urls[0].key})
        else:
            return reverse('onlineforms.views.sheet_submission_subsequent', kwargs={
                                'form_slug': self.form_submission.form.slug,
                                'formsubmit_slug': self.form_submission.slug,
                                'sheet_slug': self.sheet.slug,
                                'sheetsubmit_slug': self.slug})

    @classmethod
    def waiting_sheets_by_user(cls):
        min_age = datetime.datetime.now() - datetime.timedelta(hours=24)
        sheet_subs = SheetSubmission.objects.exclude(status='DONE').exclude(status='REJE') \
                .exclude(given_at__gt=min_age) \
                .select_related('filler__sfuFormFiller', 'filler__nonSFUFormFiller', 'form_submission__form__initiator', 'sheet')
        return itertools.groupby(sheet_subs, lambda ss: ss.filler)
        
    @classmethod
    def email_waiting_sheets(cls):
        full_url = settings.BASE_ABS_URL + reverse('onlineforms.views.index')
        subject = 'Waiting form reminder'
        from_email = "nobody@courses.cs.sfu.ca"

        filler_ss = cls.waiting_sheets_by_user()
        template = get_template('onlineforms/emails/reminder.txt')
        
        for filler, sheets in filler_ss:
            context = Context({'full_url': full_url,
                    'filler': filler, 'sheets': list(sheets)})
            msg = EmailMultiAlternatives(subject, template.render(context), from_email, [filler.email()])
            msg.send()
    
    def _send_email(self, request, template_name, subject, mail_from, mail_to, context):
        """
        Send email to user as required in various places below

        TODO: refactor out of the below functions
        """
        plaintext = get_template('onlineforms/emails/' + template_name + '.txt')
        html = get_template('onlineforms/emails/' + template_name + '.html')

        sheeturl = request.build_absolute_uri(self.get_submission_url())
        context['sheeturl'] = sheeturl
        email_context = Context(context)
        from_email = mail_from.full_email()
        to_email = mail_to.full_email()
        msg = EmailMultiAlternatives(subject, plaintext.render(email_context), from_email, [to_email])
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()


    def email_assigned(self, request, admin, assignee):
        plaintext = get_template('onlineforms/emails/sheet_assigned.txt')
        html = get_template('onlineforms/emails/sheet_assigned.html')

        full_url = request.build_absolute_uri(self.get_submission_url())
        email_context = Context({'username': admin.name(), 'assignee': assignee.name(), 'sheeturl': full_url, 'sheetsub': self})
        subject, from_email, to = 'CourSys: You have been assigned a sheet.', admin.full_email(), assignee.full_email()
        msg = EmailMultiAlternatives(subject, plaintext.render(email_context), from_email, [to])
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()

    
    def email_started(self, request):
        plaintext = get_template('onlineforms/emails/nonsfu_sheet_started.txt')
        html = get_template('onlineforms/emails/nonsfu_sheet_started.html')
    
        full_url = request.build_absolute_uri(self.get_submission_url())
        email_context = Context({'initiator': self.filler.name(), 'sheeturl': full_url, 'sheetsub': self})
        subject = '%s submission incomplete' % (self.sheet.form.title)
        from_email = "nobody@courses.cs.sfu.ca"
        to = self.filler.full_email()
        msg = EmailMultiAlternatives(subject, plaintext.render(email_context), from_email, [to])
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()

    def email_submitted(self, request, rejected=False):
        plaintext = get_template('onlineforms/emails/sheet_submitted.txt')
        html = get_template('onlineforms/emails/sheet_submitted.html')
    
        full_url = request.build_absolute_uri(reverse('onlineforms.views.view_submission',
                                    kwargs={'form_slug': self.sheet.form.slug,
                                            'formsubmit_slug': self.form_submission.slug}))
        email_context = Context({'initiator': self.filler.name(), 'adminurl': full_url, 'form': self.sheet.form,
                                 'rejected': rejected})
        subject = '%s submission' % (self.sheet.form.title)
        #from_email = self.filler.full_email()
        from_email = "nobody@courses.cs.sfu.ca"
        to = [m.person.full_email()
              for m
              in self.sheet.form.owner.formgroupmember_set.all()
              if m.email()]
        msg = EmailMultiAlternatives(subject, plaintext.render(email_context), from_email, to)
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()


    def email_returned(self, request, admin):
        context = {'admin': admin, 'sheetsub': self}
        self._send_email(request, 'sheet_returned', '%s submission returned' % (self.sheet.title),
                         admin, self.filler, context)



class FieldSubmission(models.Model):
    sheet_submission = models.ForeignKey(SheetSubmission)
    field = models.ForeignKey(Field)
    data = JSONField(null=False, blank=False, default={})
    
    __file_sub_cache = None
    def file_sub(self):
        """
        Return the (most recent) FieldSubmissionFile associated with this FieldSubmission, or None
        """
        assert self.field.fieldtype == 'FILE'
        if self.__file_sub_cache:
            # don't look up the same thing a lot unnecessarily
            return self.__file_sub_cache
        
        file_subs = FieldSubmissionFile.objects.filter(field_submission=self) \
                    .order_by('-created_at')[0:1]
        if file_subs:
            self.__file_sub_cache = file_subs[0]
            return self.__file_sub_cache
        else:
            return None
        

FormSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    fullpath = os.path.join(
            'forms',
            instance.field_submission.sheet_submission.form_submission.form.slug,
            instance.field_submission.sheet_submission.form_submission.slug,
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.field_submission_id),
            filename.encode('ascii', 'ignore'))
    return fullpath

    
class FieldSubmissionFile(models.Model):
    field_submission = models.ForeignKey(FieldSubmission, unique=True)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    file_attachment = models.FileField(storage=FormSystemStorage, null=True,
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable=False)
    
    def get_file_url(self):
        return reverse('onlineforms.views.file_field_download',
                       kwargs={'form_slug': self.field_submission.sheet_submission.sheet.form.slug,
                               'formsubmit_slug': self.field_submission.sheet_submission.form_submission.slug,
                               'file_id': self.id,
                               'action': 'get'})
    def display_filename(self):
        return os.path.basename(self.file_attachment.file.name)

class SheetSubmissionSecretUrl(models.Model):
    sheet_submission = models.ForeignKey(SheetSubmission)
    key = models.CharField(max_length=128, null=False, editable=False, unique=True)

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        if not(self.key):
            self.key = self.autokey()
        super(SheetSubmissionSecretUrl, self).save(*args, **kwargs)

    def autokey(self):
        generated = False
        attempt = str(random.randint(1000,900000000))
        while not(generated):
            old_attempt = attempt
            attempt = sha.new(attempt).hexdigest()
            if len(SheetSubmissionSecretUrl.objects.filter(key=attempt)) == 0:
                generated = True
            elif old_attempt == attempt:
                attempt = str(random.randint(1000,900000000))
        return attempt

    

ORDER_TYPE = {'UP': 'up', 'DN': 'down'}

def reorder_sheet_fields(ordered_fields, field_slug, order):
    """
    Reorder the activity in the field list of a course according to the
    specified order action. Please make sure the field list belongs to
    the same sheet.
    """
    for field in ordered_fields:
        if not isinstance(field, Field):
            raise TypeError(u'ordered_fields should be list of Field')
    for i in range(0, len(ordered_fields)):
        if ordered_fields[i].slug == field_slug:
            if (order == ORDER_TYPE['UP']) and (not i == 0):
                # swap order
                temp = ordered_fields[i-1].order
                ordered_fields[i-1].order = ordered_fields[i].order
                ordered_fields[i].order = temp
                ordered_fields[i-1].save()
                ordered_fields[i].save()
            elif (order == ORDER_TYPE['DN']) and (not i == len(ordered_fields) - 1):
                # swap order
                temp = ordered_fields[i+1].order
                ordered_fields[i+1].order = ordered_fields[i].order
                ordered_fields[i].order = temp
                ordered_fields[i+1].save()
                ordered_fields[i].save()
            break


