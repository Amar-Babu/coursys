from django.db.models.fields import TextField
from django.forms.fields import EmailField, CharField
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
from django.template.defaultfilters import linebreaksbr

class SmallTextField(FieldBase):
    more_default_config = {'min_length': 1, 'max_length': 100}
    
    class SmallTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=100, initial=1, widget=forms.TextInput(attrs={'size': 3}))
        max_length = forms.IntegerField(min_value=1, max_value=100, widget=forms.TextInput(attrs={'size': 3}))

    def make_config_form(self):
        return self.SmallTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        self.min_length = 0
        self.max_length = 0

        if self.config['min_length'] and int(self.config['min_length']) > 0:
            self.min_length = int(self.config['min_length'])
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            self.max_length = int(self.config['max_length'])

        c = forms.CharField(required=self.config['required'],
            widget=forms.TextInput(attrs=
                {'size': min(60, int(self.config['max_length'])),
                 'maxlength': int(self.config['max_length'])}),
            label=self.config['label'],
            help_text=self.config['help_text'],
            min_length=self.min_length,
            max_length=self.max_length)

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + linebreaksbr(escape(fieldsubmission.data['info'])) + '</p>')


class MediumTextField(FieldBase):
    more_default_config = {'min_length': 1, 'max_length': 1000}

    class MediumTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=1000, widget=forms.TextInput(attrs={'size': 4}))
        max_length = forms.IntegerField(min_value=1, max_value=1000, widget=forms.TextInput(attrs={'size': 4}))

    def make_config_form(self):
        return self.MediumTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        self.min_length = 0
        self.max_length = 0

        if self.config['min_length'] and int(self.config['min_length']) > 0:
            self.min_length = int(self.config['min_length'])
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            self.max_length = int(self.config['max_length'])

        c = forms.CharField(required=self.config['required'],
            widget=forms.Textarea(attrs={'cols': '60', 'rows': '3'}),
            label=self.config['label'],
            help_text=self.config['help_text'],
            min_length=self.min_length,
            max_length=self.max_length)

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + linebreaksbr(escape(fieldsubmission.data['info'])) + '</p>')


class LargeTextField(FieldBase):
    more_default_config = {'min_length': 1, 'max_length': 10000}

    class LargeTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=10000, widget=forms.TextInput(attrs={'size': 5}))
        max_length = forms.IntegerField(min_value=1, max_value=10000, widget=forms.TextInput(attrs={'size': 5}))

    def make_config_form(self):
        return self.LargeTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):

        self.min_length = 0
        self.max_length = 0

        if self.config['min_length'] and int(self.config['min_length']) > 0:
            self.min_length = int(self.config['min_length'])
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            self.max_length = int(self.config['max_length'])

        c = forms.CharField(required=self.config['required'],
            widget=forms.Textarea(attrs={'cols': '60', 'rows': '15'}),
            label=self.config['label'],
            help_text=self.config['help_text'],
            min_length=self.min_length,
            max_length=self.max_length)

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + linebreaksbr(escape(fieldsubmission.data['info'])) + '</p>')


class EmailTextField(FieldBase):
    class EmailTextConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.EmailTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.EmailField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['info']) + '</p>')


class ExplanationTextField(FieldBase):
    class ExplanationTextConfigForm(FieldConfigForm):
        text_explanation = forms.CharField(required=True, max_length=10000,
            widget=forms.Textarea(attrs={'cols': '60', 'rows': '15'}))

    def make_config_form(self):
        return self.ExplanationTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        from onlineforms.forms import ExplanationFieldWidget

        w = ExplanationFieldWidget(attrs={'class': 'disabled', 'readonly': 'readonly'})
        c = forms.CharField(required=False,
            label=self.config['label'],
            help_text=self.config['help_text'],
            widget=w)

        if 'text_explanation' in self.config:
            w.explanation = self.config['text_explanation']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + linebreaksbr(escape(self.config['text_explanation'])) + '</p>')

