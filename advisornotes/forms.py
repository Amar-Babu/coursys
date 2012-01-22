from django import forms
from advisornotes.models import AdvisorNote
from coredata.models import Person
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

class AdvisorNoteForm(forms.ModelForm):
    class Meta:
        model = AdvisorNote
        
class StudentSelect(forms.Select):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        """
        Render for jQueryUI autocomplete widget
        """
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(value)
        return mark_safe(u'<input%s />' % forms.widgets.flatatt(final_attrs))

class StudentField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(StudentField, self).__init__(*args, queryset=Person.objects.none(), widget=StudentSelect(attrs={'size': 30}), help_text="Type to search for a student.", **kwargs)
        
    def to_python(self, value):
        try:
            st = Person.objects.get(pk=value)
        except (ValueError, Person.DoesNotExist):
            raise forms.ValidationError("Unknown person selected")
        return st
    
class StudentSearchForm(forms.Form):
        search = StudentField()