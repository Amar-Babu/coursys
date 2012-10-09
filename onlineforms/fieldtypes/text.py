from django.db.models.fields import TextField
from django.forms.fields import EmailField
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms


class SmallTextField(FieldBase):
    class SmallTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=300)
        max_length = forms.IntegerField(min_value=1, max_value=300)

    def make_config_form(self):
        return SmallTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        """c = forms.CharField(required=bool(self.config['required']),
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']
        if self.config['min_length'] and int(self.config['min_length']) > 0:
            c.min_length = self.config['min_length']
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            c.max_length = self.config['max_length']
        return c"""
        return forms.CharField(label="HEY THERE", help_text="HERES WHERE THE HELP GOES")

    def serialize_field(self, field):
        return {'info': unicode(field.clean())}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['info']) + '</p>')


class MediumTextField(FieldBase):
    class MediumTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=400)
        max_length = forms.IntegerField(min_value=1, max_value=400)

    def make_config_form(self):
        return MediumTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = CharField(required=bool(self.config['required']),
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']
        if self.config['min_length'] and int(self.config['min_length']) > 0:
            c.min_length = self.config['min_length']
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            c.max_length = self.config['max_length']
        return c

    def serialize_field(self, field):
        return {'info': unicode(field.clean())}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['info']) + '</p>')


class LargeTextField(FieldBase):
    class LargeTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=500)
        max_length = forms.IntegerField(min_value=1, max_value=500)

    def make_config_form(self):
        return LargeTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = CharField(required=bool(self.config['required']),
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']
        if self.config['min_length'] and int(self.config['min_length']) > 0:
            c.min_length = self.config['min_length']
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            c.max_length = self.config['max_length']
        return c

    def serialize_field(self, field):
        return {'info': unicode(field.clean())}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['info']) + '</p>')


class EmailTextField(FieldBase):
    class EmailTextConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return EmailTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = EmailField(required=bool(self.config['required']),
            label=self.config['label'],
            help_text=self.config['help_text'])
        #c = EmailField(**self.config)

        if fieldsubmission:
            c.initial = fieldsubmission.data['email']

        return c

    def serialize_field(self, field):
        return {'email': unicode(field.clean())}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['email']) + '</p>')


class ExplanationTextField(FieldBase):
    class ExplanationTextConfigForm(FieldConfigForm):
        max_length = forms.IntegerField(min_value=1, max_value=300)
        text_explanation = forms.CharField(required=True, max_length=500)

    def make_config_form(self):
        return ExplanationTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = TextField(required=True,
            editable=False,
            label=self.config['label'],
            help_text=self.config['help_text'])

        if self.config['text_explanation']:
            c.initial = self.config['text_explanation']

        return c


    def serialize_field(self, field):
        return {'text_explanation': unicode(field.clean())}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(self.config['text_explanation']) + '</p>')

