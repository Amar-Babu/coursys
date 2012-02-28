import re
from django import forms
from django.utils.safestring import mark_safe
from django.forms.forms import BoundField
from django.forms.util import ErrorList
from django.utils.datastructures import SortedDict
from coredata.models import Member, CAMPUS_CHOICES
from ta.models import TUG, TAApplication,TAContract, CoursePreference, TACourse, TAPosting, Skill, CATEGORY_CHOICES
from ta.util import table_row__Form, update_and_return
from django.core.exceptions import ValidationError
import itertools, decimal, datetime
from django.forms.formsets import formset_factory
from django.forms.models import BaseInlineFormSet

@table_row__Form
class TUGDutyForm(forms.Form):
    label_editable = False
    def __init__(self, *args, **kwargs):
        label = kwargs.pop('label', '')
        super(TUGDutyForm, self).__init__(*args, **kwargs)
        self.label = label
    
    weekly = forms.DecimalField(label="Weekly hours", required=False)
    weekly.widget.attrs['class'] = u'weekly'
    weekly.manual_css_classes = [u'weekly']
    total = forms.DecimalField(label="Total hours")
    total.widget.attrs['class'] = u'total'
    total.manual_css_classes = [u'total']
    comment = forms.CharField(label="Comment", required=False)
    comment.widget.attrs['class'] = u'comment'
    comment.manual_css_classes = [u'comment']


class TUGDutyLabelForm(forms.Form):
    label = forms.CharField(label="Other:", 
            error_messages={'required': 'Please specify'})
    label.widget.attrs['class'] = u'label-field'

# doesn't simply subclass TUGDutyForm so that the label will be listed first
class TUGDutyOtherForm(TUGDutyLabelForm, TUGDutyForm):
    label_editable = True
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', None)
        # allow empty if this is a new TUG or if we're editing and it's empty
        kwargs['empty_permitted'] = (kwargs.get('empty_permitted', False) or
                (initial and initial.get('label')))
        super(TUGDutyOtherForm, self).__init__(*args, **kwargs)
        self.fields['label'].required = False
        self.fields['total'].required = False
        
    def as_table_row(self):
        label = self.fields.pop('label')
        html = TUGDutyForm.as_table_row(self)
        self.fields.insert(0, 'label', label)
        return html

    def clean(self):
        data = self.cleaned_data
        if (data.get('total', None) or data.get('weekly', None)) and not data.get('label', None):
            raise forms.ValidationError('Must enter label')
        return super(TUGDutyForm, self).clean()

class TUGForm(forms.ModelForm):
    '''
    userid and offering must be defined or instance must be defined.
    '''
    base_units = forms.DecimalField(min_value=0, 
            error_messages={"min_value":"Base units must be positive.",
                            "invalid":"Base units must be a number.",
                            "required":"Base units are required."})
    
    class Meta:
        model = TUG
        exclude = ('config',)
    
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None,
                 offering=None, userid=None):
        super(TUGForm, self).__init__(data, files, auto_id, prefix, initial,
                 error_class, label_suffix, empty_permitted, instance)
        # see old revisions (git id 1d1d2f9) for a dropdown
        if userid is not None and offering is not None:
            member = Member.objects.get(person__userid=userid, offering=offering)
        elif instance is not None:
            member = instance.member
        else:
            assert False
        
        self.initial['member'] = member
        self.fields['member'].widget = forms.widgets.HiddenInput()
        
        self.subforms = self.__construct_subforms(data, initial, instance)
        
    def __construct_subforms(self, data, initial, instance):
        # this function is a simplification/clarification of this one liner:
        # return SortedDict((field, klass(prefix=field, data=data, 
        #  initial=(instance.config[field] if instance and field in instance.config 
        #  else initial[field] if initial and field in initial else None), 
        #  label=TUG.config_meta[field]['label'] if field in TUG.config_meta else '')) 
        #  for field, klass in itertools.chain(((f, TUGDutyForm) for f in TUG.regular_fields), 
        #  ((f, TUGDutyOtherForm) for f in TUG.other_fields)))
        field_names_and_formclasses = itertools.chain(
                ((f, TUGDutyForm) for f in TUG.regular_fields),
                ((f, TUGDutyOtherForm) for f in TUG.other_fields))
        
        get_label = lambda field: TUG.config_meta[field]['label'] if field in TUG.config_meta else ''
        
        get_initial = lambda field: None
        if instance:
            if initial:
                get_initial = lambda field:(instance.config[field] 
                        if field in instance.config else 
                        initial.get(field, None))
            else:
                get_initial = lambda field:instance.config.get(field, None)
        elif initial:
            get_initial = lambda field:initial.get(field, None)
        
        return SortedDict(
                (field, 
                 klass(prefix=field, data=data, 
                       initial=get_initial(field),
                       label=get_label(field))) 
                    for field, klass in field_names_and_formclasses)
        
    def clean_member(self):
        if self.cleaned_data['member'] != self.initial['member']:
            raise forms.ValidationError("Wrong member")
        return self.cleaned_data['member']
    def is_valid(self):
        return (all(form.is_valid() for form in self.subforms.itervalues()) 
                and super(TUGForm, self).is_valid())
    def full_clean(self):
        for form in self.subforms.itervalues():
            form.full_clean()
        return super(TUGForm, self).full_clean()
    def clean(self):
        data = super(TUGForm, self).clean()
        try: data['config'] = SortedDict((field, self.subforms[field].cleaned_data) 
                for field in TUG.all_fields)
        except AttributeError: pass
        return data
    def save(self, *args, **kwargs):
        # TODO: load data from config_form into JSONField
#        self.instance
        self.instance.config = self.cleaned_data['config']
        return super(TUGForm, self).save(*args, **kwargs)
    
class TAApplicationForm(forms.ModelForm):
    class Meta:
        model = TAApplication
        exclude = ('posting','person','skills','campus_preferences')
        widgets = {
                   'base_units': forms.TextInput(attrs={'size': 5}),
                   'sin': forms.TextInput(attrs={'size': 9}),
                   }

    def clean_sin(self):
        sin = self.cleaned_data['sin']
        sin = re.sub('[ -]+','',str(sin))
        if not re.match('\d{9}$',sin):
            raise forms.ValidationError("Invalid SIN")
        return sin

class CoursePreferenceForm(forms.ModelForm):

    class Meta:
        model = CoursePreference
        exclude = ('app',) 

class TAContractForm(forms.ModelForm):
 
    #pay_per_bu = forms.DecimalField(max_digits=8, decimal_places=2)
    #scholarship_per_bu = forms.DecimalField(max_digits=8, decimal_places=2) 
          
    def __init__(self, *args, **kwargs):
        super(TAContractForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        
        if instance and instance.id:
            del self.fields['applicant']
    
    def clean_pay_per_bu(self):
        pay = self.cleaned_data['pay_per_bu']
        try:
            pay = decimal.Decimal(pay).quantize(decimal.Decimal('1.00'))
        except decimal.InvalidOperation:
            raise forms.ValidationError("Pay per BU values must be numbers")
        return pay
    
        
    class Meta:
        model = TAContract
        exclude = ['ta_posting', 'created_by']
                
    def clean_sin(self):
        sin = self.cleaned_data['sin']
        sin = re.sub('[ -]+','',str(sin))
        if not re.match('\d{9}$',sin):
            raise forms.ValidationError("Invalid SIN")
        return sin
        
    def clean_pay_start(self):
        start = self.cleaned_data['pay_start']
        return start

    def clean_pay_end(self):
        end = self.cleaned_data['pay_end']
        if 'pay_start' in self.cleaned_data:
            start = self.cleaned_data['pay_start']
            if start >= end:
                raise forms.ValidationError("Contracts must end after they start")
        return end
    
    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        today = datetime.date.today()
        if deadline < today:
            raise forms.ValidationError("Deadline for acceptance cannot be before today")
        return deadline
    
    

    

class TACourseForm(forms.ModelForm):   
           
    class Meta:
        model = TACourse
        exclude = ('contract',) 

class BaseTACourseFormSet(BaseInlineFormSet):    
    def clean(self):
        self.validate_unique()
        
        #check at least one course selected
        count = 0
        if any(self.errors):
            return
        for form in self.forms:
            try:
                if form.cleaned_data:
                    count += 1
            except AttributeError:
                pass
        if count < 1:
            raise forms.ValidationError(u"Please select at least one course")
        
        #check no duplicate course selection
        courses = []
        for form in self.forms:
            if form.cleaned_data and form.cleaned_data['course']:
                course = form.cleaned_data['course']
                if(course in courses):
                        raise forms.ValidationError(u"Duplicate course selection")
                courses.append(course)  
        
# helpers for the TAPostingForm
class LabelTextInput(forms.TextInput):
    "TextInput with a bonus label"
    def __init__(self, label, *args, **kwargs):
        self.label = label
        super(LabelTextInput, self).__init__(*args, **kwargs)
    def render(self, *args, **kwargs):
        return " " + self.label + ": " + super(LabelTextInput, self).render(*args, **kwargs)

class PayWidget(forms.MultiWidget):
    "Widget for entering salary/scholarship values"
    def __init__(self, *args, **kwargs):
        widgets = [LabelTextInput(label=c[0], attrs={'size': 6}) for c in CATEGORY_CHOICES]
        kwargs['widgets'] = widgets
        super(PayWidget, self).__init__(*args, **kwargs)
    
    def decompress(self, value):
        # should already be a list: if we get here, have no defaults
        return [0]*len(CATEGORY_CHOICES)

class PayField(forms.MultiValueField):
    "Field for entering salary/scholarship values"
    def __init__(self, *args, **kwargs):
        fields = [forms.CharField() for _ in CATEGORY_CHOICES]
        kwargs['fields'] = fields
        kwargs['widget'] = PayWidget()
        super(PayField, self).__init__(*args, **kwargs)

    def compress(self, values):
        return values


class TAPostingForm(forms.ModelForm):
    start = forms.DateField(label="Contract Start", help_text='Default start date for contracts')
    end = forms.DateField(label="Contract End", help_text='Default end date for contracts')
    salary = PayField(label="Salary per BU", help_text="Default pay rates for contracts")
    scholarship = PayField(label="Scholarship per BU", help_text="Default scholarship rates for contracts")
    payperiods = forms.IntegerField(label="Pay periods", help_text='Number of pay periods in the semester',
            max_value=20, min_value=1, widget=forms.TextInput(attrs={'size': 5}))
    excluded = forms.MultipleChoiceField(help_text="Courses that should <strong>not</strong> be selectable for TA positions",
            choices=[], required=False, widget=forms.SelectMultiple(attrs={'size': 15}))
    skills = forms.CharField(label="Skills", help_text='Skills to ask applicants about: one per line', required=False,
                          widget=forms.Textarea())

    # TODO: sanity-check the dates against semester start/end
    
    class Meta:
        model = TAPosting
        exclude = ('config',) 
    
    def __init__(self, *args, **kwargs):
        super(TAPostingForm, self).__init__(*args, **kwargs)
        # populat initial data fron instance.config
        self.initial['salary'] = self.instance.salary()
        self.initial['scholarship'] = self.instance.scholarship()
        self.initial['start'] = self.instance.start()
        self.initial['end'] = self.instance.end()
        self.initial['excluded'] = self.instance.excluded()
        self.initial['payperiods'] = self.instance.payperiods()
        skills = Skill.objects.filter(posting=self.instance)
        self.initial['skills'] = '\n'.join((s.name for s in skills))
    
    def clean_payperiods(self):
        payperiods = self.cleaned_data['payperiods']
        self.instance.config['payperiods'] = payperiods
        return payperiods

    def clean_start(self):
        start = self.cleaned_data['start']
        self.instance.config['start'] = unicode(start)
        return start

    def clean_end(self):
        end = self.cleaned_data['end']
        if 'start' in self.cleaned_data:
            start = self.cleaned_data['start']
            if start >= end:
                raise forms.ValidationError("Contracts must end after they start")
        self.instance.config['end'] = unicode(end)
        return end
        
    def clean_opens(self):
        opens = self.cleaned_data['opens']
        today = datetime.date.today()
        if opens < today:
            raise forms.ValidationError("Postings cannot open before today")
        return opens

    def clean_closes(self):
        closes = self.cleaned_data['closes']
        today = datetime.date.today()
        if closes <= today:
            raise forms.ValidationError("Postings must close after today")
        if 'opens' in self.cleaned_data:
            opens = self.cleaned_data['opens']
            if opens >= closes:
                raise forms.ValidationError("Postings must close after they open")
        return closes
        
    def clean_salary(self):
        sals = self.cleaned_data['salary']
        try:
            sals = [decimal.Decimal(s).quantize(decimal.Decimal('1.00')) for s in sals]
        except decimal.InvalidOperation:
            raise forms.ValidationError("Salary values must be numbers")
        
        self.instance.config['salary'] = [str(s) for s in sals]
        return sals
    
    def clean_scholarship(self):
        schols = self.cleaned_data['scholarship']
        try:
            schols = [decimal.Decimal(s).quantize(decimal.Decimal('1.00')) for s in schols]
        except decimal.InvalidOperation:
            raise forms.ValidationError("Scholarship values must be numbers")

        self.instance.config['scholarship'] = [str(s) for s in schols]
        return schols
    
    def clean_excluded(self):
        excluded = self.cleaned_data['excluded']
        excluded = [int(e) for e in excluded]
        self.instance.config['excluded'] = excluded
        return excluded
    
    def clean_skills(self):
        skills = self.cleaned_data['skills']
        skills = [s.strip() for s in skills.split("\n")]
        old_skills = Skill.objects.filter(posting=self.instance)
        res = []
        for i, skill in enumerate(skills):
            if len(old_skills) < i+1:
                # nothing existing
                new = Skill(posting=self.instance, name=skill, position=i)
                res.append(new)
            else:
                # update old
                old = old_skills[i]
                old.name = skill
                res.append(old)
        return res

class BUForm(forms.Form):
    students = forms.IntegerField(min_value=0, max_value=1000)
    bus = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2)

BUFormSet = formset_factory(BUForm, extra=10)
LEVEL_CHOICES = (
                 ('100', '100-level'),
                 ('200', '200-level'),
                 ('300', '300-level'),
                 ('400', '400-level'),
                 )
class TAPostingBUForm(forms.Form):
    level = forms.ChoiceField(choices=LEVEL_CHOICES)
