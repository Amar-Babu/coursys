import datetime

from django.db import models

from autoslug import AutoSlugField
from jsonfield import JSONField

from coredata.models import Unit, Person
from courselib.json_fields import getter_setter
from courselib.slugs import make_slug

from faculty.event_types.career import AppointmentEventHandler, SalaryBaseEventHandler

# CareerEvent.event_type value -> CareerEventManager class
EVENT_TYPE_CHOICES = [
    ('APPOINT', AppointmentEventHandler),
    ('SALARY', SalaryBaseEventHandler),
    ]
EVENT_TYPES = dict(EVENT_TYPE_CHOICES)


class CareerEvent(models.Model):
    # ...

    def save(self, editor, *args, **kwargs):
        assert editor.__class__.__name__ == 'Person' # we're doing to so we can add an audit trail later.

        res = super(CareerEvent, self).save(*args, **kwargs)
        return res


class DocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    pass


class MemoTemplate(models.Model):
    """
    A template for memos.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=250, null=False)
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES)
    template_text = models.TextField(help_text="I.e. 'Congratulations {{first_name}} on ... '")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Memo template created by.')
    hidden = models.BooleanField(default=False)

    def autoslug(self):
        return make_slug(self.unit.label + "-" + self.label)  
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False)
    class Meta:
        unique_together = ('unit', 'label')      
    def __unicode__(self):
        return u"%s in %s" % (self.label, self.unit)


class Memo(models.Model):
    """
    A memo created by the system, and attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False)

    sent_date = models.DateField(default=datetime.date.today, help_text="The sending date of the letter, editable")
    to_lines = models.TextField(help_text='Delivery address for the letter', null=True, blank=True)
    from_person = models.ForeignKey(Person, null=True)
    from_lines = models.TextField(help_text='Name (and title) of the signer, e.g. "John Smith, Applied Sciences, Dean"')
    subject = models.TextField(help_text='The career event of the memo')
    
    template = models.ForeignKey(MemoTemplate)
    memo_text = models.TextField(help_text="I.e. 'Congratulations Mr. Baker on ... '")
    salutation = models.CharField(max_length=100, default="To whom it may concern", blank=True)
    closing = models.CharField(max_length=100, default="Sincerely")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Letter generation requseted by.')
    hidden = models.BooleanField(default=False)
    config = JSONField(default={}) # addition configuration for within the memo
        

    # 'use_sig': use the from_person's signature if it exists? (Users set False when a real legal signature is required.)
    
    defaults = {'use_sig': True}
    use_sig = property(*getter_setter('use_sig'))
        
    """ need career event slugs
    def autoslug(self):
        return make_slug(self.career_event.slug + "-" + self.template.memo_type)     
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)            
    def __unicode__(self):
        return u"%s letter for %s" % (self.template.label, self.student)
    """
    def save(self, *args, **kwargs):
        # normalize text so it's easy to work with
        if not self.to_lines:
            self.to_lines = ''
        _normalize_newlines(self.to_lines.rstrip())
        self.from_lines = _normalize_newlines(self.from_lines.rstrip())
        self.memo_text = _normalize_newlines(self.content.rstrip())
        self.memo_text = many_newlines.sub('\n\n', self.content)
        super(Memo, self).save(*args, **kwargs)


