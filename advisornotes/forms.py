from advisornotes.models import AdvisorNote, NonStudent, ArtifactNote, Artifact, AdvisorVisit, AdvisorVisitCategory
from coredata.models import Person
from coredata.forms import OfferingField, CourseField
from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.models import ModelForm
from courselib.markup import MarkupContentMixin, MarkupContentField
import datetime

TEXT_WIDTH = 70


class AdvisorNoteForm(MarkupContentMixin(field_name='text'), forms.ModelForm):
    text = MarkupContentField(label="Content", default_markup='plain', allow_math=False, restricted=False, with_wysiwyg=True)
    email_student = forms.BooleanField(required=False,
                                       help_text="Should the student be emailed the contents of this note?")

    def __init__(self, student, *args, **kwargs):
        # Only needed for the clean_email_student below, so that we may check for an email and display a validation
        # error if needed.  The view handles sending the actual email afterwards.
        self.student = student
        super().__init__(*args, **kwargs)

    def clean_email_student(self):
        email = self.cleaned_data['email_student']
        if email and not self.student.email():
            raise ValidationError("We don't have an email address for this student: cannot email them here.")
        return email

    class Meta:
        model = AdvisorNote
        exclude = ('hidden', 'emailed', 'created_at', 'config')


class ArtifactNoteForm(forms.ModelForm):
    class Meta:
        model = ArtifactNote
        exclude = ('hidden', 'course', 'course_offering', 'artifact',)
        widgets = {
                'text': forms.Textarea(attrs={'cols': TEXT_WIDTH, 'rows': 15})
                }


class EditArtifactNoteForm(forms.ModelForm):
    class Meta:
        model = ArtifactNote
        exclude = ('hidden', 'course', 'course_offering', 'artifact', 'category', 'text', 'file_attachment', 'unit',)
        widgets = {
                'text': forms.Textarea(attrs={'cols': TEXT_WIDTH, 'rows': 15})
                }

class StudentSelect(forms.TextInput):
    pass


class StudentField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(StudentField, self).__init__(*args, queryset=Person.objects.none(), widget=StudentSelect(attrs={'size': 25}), help_text="Type to search for a student.", **kwargs)

    def to_python(self, value):
        try:
            st = Person.objects.get(emplid=value)
            return st
        except:
            pass

        try:
            st = NonStudent.objects.get(slug=value)
        except (ValueError, NonStudent.DoesNotExist):
            raise forms.ValidationError("Could not find person's record.")

        return st


class StudentSearchForm(forms.Form):
    search = StudentField()


class NoteSearchForm(forms.Form):
    search = forms.CharField()


class ArtifactSearchForm(forms.Form):
    search = forms.CharField()


class OfferingSearchForm(forms.Form):
    offering = OfferingField()
class CourseSearchForm(forms.Form):
    course = CourseField()

class StartYearField(forms.IntegerField):

    def validate(self, value):
        super(StartYearField, self).validate(value)
        if value is not None:
            super(StartYearField, self).validate(value)
            current_year = datetime.date.today().year
            if value < current_year:
                raise forms.ValidationError("Must be equal to or after %d" % current_year)


class NonStudentForm(ModelForm):
    start_year = StartYearField(help_text="The predicted/potential start year", required=True)

    class Meta:
        model = NonStudent
        exclude = ('config', 'notes')


class ArtifactForm(forms.ModelForm):
    class Meta:
        model = Artifact
        exclude = ('config',)


class MergeStudentField(forms.Field):

    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            raise ValidationError(self.error_messages['required'])
        try:
            value = int(value)
        except ValueError:
            raise forms.ValidationError("Invalid format")
        try:
            student = Person.objects.get(emplid=value)
        except Person.DoesNotExist:
            raise forms.ValidationError("Could not find student record")
        return student


class MergeStudentForm(forms.Form):

    student = MergeStudentField(label="Student #")

class AdvisorVisitCategoryForm(forms.ModelForm):
    class Meta:
        model = AdvisorVisitCategory
        exclude = ['config']
