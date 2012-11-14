from coredata.forms import PersonField
from django import forms
from django.forms.models import ModelForm
from onlineforms.models import Form, Sheet, Field, FormSubmission, FIELD_TYPE_CHOICES, FIELD_TYPE_MODELS, FormGroup, VIEWABLE_CHOICES, NonSFUFormFiller
from django.utils.safestring import mark_safe
from django.utils.html import escape

class DividerFieldWidget(forms.TextInput):
  def render(self, name, value, attrs=None):
    return mark_safe('<hr />')

class ExplanationFieldWidget(forms.Textarea):
  def render(self, name, value, attrs=None):
    return mark_safe('<div>%s</div>' % escape(value))

# Manage groups
class GroupForm(ModelForm):
    class Meta:
        model = FormGroup
        exclude = ('members',)

class EditGroupForm(ModelForm):
    class Meta:
        model = FormGroup
        fields = ('name',)

class EmployeeSearchForm(forms.Form):
    search = PersonField()

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(EmployeeSearchForm, self).is_valid(*args, **kwargs)

# Manage forms
class FormForm(ModelForm):
    class Meta:
        model = Form
	exclude = ('active', 'original', 'unit')
        
class SheetForm(forms.Form):
    title = forms.CharField(required=True, max_length=30, label=mark_safe('Title'), help_text='Name of the sheet')
    can_view = forms.ChoiceField(required=True, choices=VIEWABLE_CHOICES, label='Can view')

class EditSheetForm(ModelForm):
    class Meta:
        model = Sheet

class NonSFUFormFillerForm(ModelForm):
    class Meta:
        model = NonSFUFormFiller

class FieldForm(forms.Form):
    type = forms.ChoiceField(required=True, choices=FIELD_TYPE_CHOICES, label='Type')

# Administrate forms 
class AdminAssignSheet(forms.Form):
    class FormModelChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj):
            return obj.title    
        
    assignee = PersonField(label='Assign to', required=False)
    """email = forms.EmailField(required=False,
                label='Assign to e-mail',
                help_text='Assign this form to an external email address.')"""
    
    def __init__(self, label, query_set, *args, **kwargs):
        super(AdminAssignSheet, self).__init__(*args, **kwargs)
        self.fields.insert(0, label, self.FormModelChoiceField(required=True, 
            queryset=query_set, 
            label=label.capitalize()))

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(AdminAssignSheet, self).is_valid(*args, **kwargs)

class AdminAssignForm(AdminAssignSheet):
    class FormGroupModelChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj):
            return obj.name  
    
    def __init__(self, form_groups, label, query_set, *args, **kwargs):
        super(AdminAssignForm, self).__init__(label, query_set, *args, **kwargs)
        self.fields.insert(1, 'form_group', 
            self.FormGroupModelChoiceField(required=True, queryset=form_groups, label='Form Group'))
		
class DynamicForm(forms.Form):
    def __init__(self, title, *args, **kwargs):
        self.title = title
        super(DynamicForm, self).__init__(*args, **kwargs)

    def setFields(self, kwargs):
        """
        Sets the fields in a form
        """
        keys = kwargs.keys()

        # Determine order right here
        keys.sort()

        for k in keys:
            self.fields[k] = kwargs[k]

    def fromFields(self, fields, field_submissions=[]):
        """
        Sets the fields from a list of field model objects
        preserving the order they are given in
        """
        # create a dictionary so you can find a fieldsubmission based on a field
        field_submission_dict = {}
        for field_submission in field_submissions:
            field_submission_dict[field_submission.field] = field_submission
        fieldargs = {}
        # keep a dictionary of the configured display fields, so we can serialize them with data later
        self.display_fields = {}
        for (counter, field) in enumerate(fields):
            # get the field
            display_field = FIELD_TYPE_MODELS[field.fieldtype](field.config)
            # make the form field, using the form submission data if it exists
            if field in field_submission_dict:
                self.fields[counter] = display_field.make_entry_field(field_submission_dict[field])
            else:
                self.fields[counter] = display_field.make_entry_field()
            # keep the display field for later
            self.display_fields[self.fields[counter] ] = display_field


    def fromPostData(self, post_data, ignore_required=False):
        self.cleaned_data = {}
        for name, field in self.fields.items():
            try:
                if isinstance(field, forms.MultiValueField):
                    # handle {name}_{i} names from POST data
                    i = 0
                    cleaned_data = []
                    while True:
                        n = str(name) + '_' + str(i)
                        if n not in post_data:
                            break
                        if post_data[n]:
                            cleaned_data.append(post_data[n])
                        i += 1
                elif str(name) in post_data:
                    if ignore_required and post_data[str(name)] == "":
                        cleaned_data = ""
                    else:
                        cleaned_data = field.clean(post_data[str(name)])
                else:
                    if ignore_required:
                        cleaned_data = ""
                    else:
                        cleaned_data = field.clean("")
                self.cleaned_data[str(name)] = cleaned_data
                field.initial = cleaned_data
            except forms.ValidationError, e:
                self.errors[name] = ", ".join(e.messages)
                field.initial = post_data[str(name)]

    def is_valid(self):
        # override because I'm not sure how to bind this form to data (i.e. form.is_bound)
        return not bool(self.errors)

    def validate(self, post):
        """
        Validate the contents of the form
        """
        for name, field in self.fields.items():
            try:
                field.clean(post[str(name)])
            except Exception, e:
                self.errors[name] = e.message
