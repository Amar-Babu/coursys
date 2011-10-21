from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput, SelectMultiple
from django import forms
from django.http import HttpResponse
from jsonfield import JSONField

OFFICE_TYPES = [ # (label, internal identifier, extensions)
        ('MS Word', 'MS-WORD', ['.doc', '.docx']),
        ('MS Excel', 'MS-EXCEL', ['.xls', '.xlsx']),
        ('MS Powerpoint', 'MS-PPT', ['.ppt', '.pptx']),
        ('MS Project', 'MS-PROJ', ['.mpp']),
        ('MS Visio', 'MS-VISIO', ['.vsd']),
        ('OpenDocument Text', 'OD-TEXT', ['.odt']),
        ('OpenDocument Presentation', 'OD-PRES', ['.odp']),
        ('OpenDocument Spreadsheet', 'OD-SS', ['.ods']),
        ('OpenDocument Graphics', 'OD-GRA', ['.odh']),
        ]

OFFICE_CHOICES = [(ident, label) for label, ident, exts in OFFICE_TYPES]
OFFICE_LABELS = dict(((ident, label) for label, ident, exts in OFFICE_TYPES))

class OfficeComponent(SubmissionComponent):
    "An office document submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the Office file, in kB.", null=False, default=10000)
    allowed = JSONField(max_length=500, null=False, help_text='Accepted file extensions.')

    def get_allowed_list(self):
        return self.allowed['types']
    def get_allowed_display(self):
        return ", ".join((OFFICE_LABELS[ident] for ident in self.allowed['types']))
    allowed_types = dict(((ident, exts) for label, ident, exts in OFFICE_TYPES))

    mime_types = {
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".mpp": "application/vnd.ms-project",
            ".vsd": "application/visio",
            ".odt": "application/vnd.oasis.opendocument.text", 
            ".odp": "application/vnd.oasis.opendocument.presentation", 
            ".ods": "application/vnd.oasis.opendocument.spreadsheet", 
            ".odg": "application/vnd.oasis.opendocument.graphics", 
            }
    class Meta:
        app_label = 'submission'


class SubmittedOffice(SubmittedComponent):
    component = models.ForeignKey(OfficeComponent, null=False)
    office = models.FileField(upload_to=submission_upload_path, blank=False, max_length=500, storage=SubmissionSystemStorage)
        
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.office.url
    def get_size(self):
        try:
            return self.office.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.office.name)[1]

    def download_response(self):
        # figure out the MIME type
        for ext in self.component.mime_types:
            if self.office.name.lower().endswith(ext):
                mimetype = self.component.mime_types[ext]
                break

        response = HttpResponse(mimetype=mimetype)
        self.sendfile(self.office, response)
        return response

    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.office, prefix)
        zipfile.write(self.office.path, filename)

class Office:
    label = "office"
    name = "Office"
    descr = "an Office file"
    Component = OfficeComponent
    SubmittedComponent = SubmittedOffice
    
    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = OfficeComponent
            fields = ['title', 'description', 'allowed', 'max_size', 'specified_filename', 'deleted']
        def __init__(self, *args, **kwargs):
            super(Office.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})
            self.fields['max_size'].label=mark_safe("Max size"+submission.forms._required_star)

            self.fields['allowed'].widget = SelectMultiple(choices=OFFICE_CHOICES, attrs={'style':'width:40em', 'size': 15})
            self.initial['allowed'] = self._initial_allowed
            self.fields['allowed'].label=mark_safe("Allowed Types"+submission.forms._required_star)

        def _initial_allowed(self):
            """
            Rework the comma-separated value into a list for the SelectMultiple initial value
            """
            if self.instance and 'types' in self.instance.allowed:
                return self.instance.allowed['types']
            else:
                return []

        def clean_allowed(self):
            data = self.data.getlist('allowed')
            if len(data)==0:
                raise forms.ValidationError("No file types selected")
            return {'types': data}


    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedOffice
            fields = ['office']
            widgets = {'office': FileInput()}
        def clean_office(self):
            data = self.cleaned_data['office']
            return self.check_uploaded_data(data)

SubmittedOffice.Type = Office
OfficeComponent.Type = Office
