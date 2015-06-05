import fractions

from django import forms

from coredata.models import Unit

from faculty.event_types import fields, search
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.choices import Choices
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent


class ExternalAffiliationHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'EXTERN_AFF'
    NAME = 'External Affiliation'

    TO_HTML_TEMPLATE = '''
        {% extends 'faculty/event_base.html' %}{% load event_display %}{% block dl %}
        <dt>Organization Name</dt><dd>{{ handler|get_display:'org_name' }}</dd>
        <dt>Organization Type</dt><dd>{{ handler|get_display:'org_type'}}</dd>
        <dt>Organization Class</dt><dd>{{ handler|get_display:'org_class'}}</dd>
        <dt>Is Research Institute / Centre?</dt><dd>{{ handler|get_display:'is_research'|yesno }}</dd>
        <dt>Is Adjunct?</dt><dd>{{ handler|get_display:'is_adjunct'|yesno }}</dd>
        {% endblock %}
    '''

    class EntryForm(BaseEntryForm):

        ORG_TYPES = Choices(
            ('SFU', 'Internal SFU'),
            ('ACADEMIC', 'Academic'),
            ('PRIVATE', 'Private Sector'),
        )
        ORG_CLASSES = Choices(
            ('EXTERN_COMP', 'External Company'),
            ('NO_PROFIT', 'Not-For-Profit Institution'),
        )

        org_name = forms.CharField(label='Organization Name', max_length=255)
        org_type = forms.ChoiceField(label='Organization Type', choices=ORG_TYPES)
        org_class = forms.ChoiceField(label='Organization Classification', choices=ORG_CLASSES)
        is_research = forms.BooleanField(label='Research Institute/Centre?', required=False)
        is_adjunct = forms.BooleanField(label='Adjunct?', required=False)

    SEARCH_RULES = {
        'org_name': search.StringSearchRule,
        'org_type': search.ChoiceSearchRule,
        'org_class': search.ChoiceSearchRule,
        'is_adjunct': search.BooleanSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'org_name',
        'org_type',
        'org_class',
        'is_adjunct',
    ]

    def get_org_type_display(self):
        return self.EntryForm.ORG_TYPES.get(self.get_config('org_type'))

    def get_org_class_display(self):
        return self.EntryForm.ORG_CLASSES.get(self.get_config('org_class'))

    def short_summary(self):
        org_name = self.get_config('org_name')
        return 'Affiliated with {}'.format(org_name)


class CommitteeMemberHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'COMMITTEE'
    NAME = 'Committee Member'
    config_name = 'Committee'

    TO_HTML_TEMPLATE = '''
        {% extends 'faculty/event_base.html' %}{% load event_display %}{% block dl %}
        <dt>Committee Name</dt><dd>{{ handler|get_display:'committee_name' }}</dd>
        <dt>Committee Unit</dt><dd>{{ handler|get_display:'committee_unit' }}</dd>
        {% endblock %}
    '''

    class EntryForm(BaseEntryForm):

        committee_name = forms.CharField(label='Committee Name', max_length=255)
        committee_unit = forms.ModelChoiceField(label='Committee Unit',
                                                queryset=Unit.objects.all())

    SEARCH_RULES = {
        'committee_name': search.StringSearchRule,
        'committee_unit': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'committee_name',
        'committee_unit',
    ]

    class ConfigItemForm(CareerEventHandlerBase.ConfigItemForm):
        flag_short = forms.CharField(label='Committee short form', help_text='e.g. UGRAD')
        flag = forms.CharField(label='Committee full name', help_text='e.g. Undergraduate Program Committee')

        def clean_flag_short(self):
            """
            Make sure the flag is globally-unique.
            """
            flag_short = self.cleaned_data['flag_short']
            CommitteeMemberHandler.ConfigItemForm.check_unique_key('COMMITTEEE', 'committees', flag_short, 'committee')
            return flag_short

        def save_config(self):
            from faculty.models import EventConfig
            ec, _ = EventConfig.objects.get_or_create(unit=self.unit_object, event_type='FELLOW')
            fellows = ec.config.get('committees', [])
            fellows.append([self.cleaned_data['flag_short'], self.cleaned_data['flag'], 'ACTIVE'])
            ec.config['committees'] = fellows
            ec.save()

    def get_committee_unit_display(self):
        unit = self.get_config('committee_unit', '')
        if unit:
            return unit.informal_name()
        else:
            return '???'

    def get_committee_unit_display_short(self):
        unit = self.get_config('committee_unit', None)
        if unit:
            return unit.label
        else:
            return '???'

    def short_summary(self):
        name = self.get_config('committee_name', '')
        unit = self.get_committee_unit_display_short()
        return 'Committee member: {} ({})'.format(name, unit)


class ResearchMembershipHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'LABMEMB'
    NAME = 'Research Group / Lab Membership'

    TO_HTML_TEMPLATE = '''
        {% extends 'faculty/event_base.html' %}{% load event_display %}{% block dl %}
        <dt>Lab Name</dt><dd>{{ handler|get_config:'lab_name' }}</dd>
        <dt>Location</dt><dd>{{ handler|get_config:'location' }}</dd>
        {% endblock %}
        '''

    class EntryForm(BaseEntryForm):

        LOCATION_TYPES = Choices(
            ('SFU', 'Internal SFU'),
            ('ACADEMIC', 'Other Academic'),
            ('EXTERNAL', 'External'),
        )

        lab_name = forms.CharField(label='Research Group / Lab Name', max_length=255)
        location = forms.ChoiceField(choices=LOCATION_TYPES)

    SEARCH_RULES = {
        'lab_name': search.StringSearchRule,
        'location': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'lab_name',
        'location',
    ]

    def get_location_display(self):
        return self.EntryForm.LOCATION_TYPES.get(self.get_config('location'), 'N/A')

    def short_summary(self):
        return 'Member of {}'.format(self.get_config('lab_name'))


class ExternalServiceHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    External Service
    """

    EVENT_TYPE = 'EXTSERVICE'
    NAME = "External Service"

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Description</dt><dd>{{ handler|get_display:"description" }}</dd>
        <dt>Add Pay</dt><dd>${{ handler|get_display:"add_pay" }}</dd>
        <dt>Teaching Credits</dt><dd>{{ handler|get_display:"teaching_credits" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        description = forms.CharField(help_text='A brief description of the service', max_length=30)
        add_pay = fields.AddPayField()
        teaching_credits = fields.TeachingCreditField()

    def short_summary(self):
        return 'External Service: %s' % (self.get_config('description'))

    def salary_adjust_annually(self):
        add_pay = self.get_config('add_pay')
        return SalaryAdjust(0, 1, add_pay)

    def teaching_adjust_per_semester(self):
        credits = self.get_config('teaching_credits')
        return TeachingAdjust(credits, fractions.Fraction(0))


class SpecialDealHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'SPCL_DEAL'
    NAME = 'Special Deal'

    class EntryForm(BaseEntryForm):
        description = forms.CharField(help_text='A brief description of the deal', max_length=30)
        def post_init(self):
            self.fields['comments'].help_text = 'Enter details about the special deal.'
            self.fields['comments'].required = True

    def short_summary(self):
        return 'Special Deal: {}'.format(self.get_config('description'))

class OtherEventHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'OTHER_NOTE'
    NAME = 'Other Event / Note'

    class EntryForm(BaseEntryForm):

        def post_init(self):
            self.fields['comments'].help_text = 'Enter details about the event or note here.'
            self.fields['comments'].required = True

    def short_summary(self):
        return 'Other Event / Note'
