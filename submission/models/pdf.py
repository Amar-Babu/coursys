from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput
from django import forms
from django.http import HttpResponse

class PDFComponent(SubmissionComponent):
    "A Acrobat (PDF) submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the PDF file, in kB.", null=False, default=5000)
    allowed_types = {
            "PDF": [".pdf"]
            }
    class Meta:
        app_label = 'submission'


class SubmittedPDF(SubmittedComponent):
    component = models.ForeignKey(PDFComponent, null=False)
    pdf = models.FileField(upload_to=submission_upload_path, blank=False, storage=SubmissionSystemStorage)
        
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.pdf.url
    def get_size(self):
        return self.pdf.size

    def download_response(self):
        response = HttpResponse(mimetype="application/pdf")
        self.sendfile(self.pdf, response)
        return response
    def add_to_zip(self, zipfile):
        filename = self.file_filename(self.pdf)
        zipfile.write(self.pdf.path, filename)

class PDF:
    label = "pdf"
    name = "PDF"
    Component = PDFComponent
    SubmittedComponent = SubmittedPDF
    
    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = PDFComponent
            fields = ['title', 'description', 'max_size']
            widgets = {
                'description': Textarea(attrs={'cols': 50, 'rows': 5}),
                'max_size': TextInput(attrs={'style':'width:5em'}),
            }

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedPDF
            fields = ['pdf']
            widgets = {'pdf': FileInput()}
        def clean_pdf(self):
            data = self.cleaned_data['pdf']
            return self.check_uploaded_data(data)

SubmittedPDF.Type = PDF
PDFComponent.Type = PDF
