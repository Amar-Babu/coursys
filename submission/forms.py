from django import forms
from submission.models import *
from django.forms.widgets import Textarea, TextInput, FileInput
from django.forms import ModelForm, URLField
from django.conf import settings
from django.utils.safestring import mark_safe
import urllib


_required_star = '<em><img src="'+settings.MEDIA_URL+'icons/required_star.gif" alt="required"/></em>'

class ComponentForm(ModelForm):
    #override title to have 'required star'
    title = forms.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")', label=mark_safe("Title"+_required_star))
    specified_filename = forms.CharField(max_length=200, help_text="Specify the name of the file to be submitted.  Leave blank to accept any file name.", label="File name", required=False)


#class ArchiveComponentForm(ComponentForm):
#    class Meta:
#        model = ArchiveComponent
#        fields = ['title', 'description', 'max_size']
#        widgets = {
#            'description': Textarea(attrs={'cols': 50, 'rows': 5}),
#            'max_size': TextInput(attrs={'style':'width:5em'}),
#        }

#class URLComponentForm(ComponentForm):
#    class Meta:
#        model = URLComponent
#        fields = ['title', 'description']
#        widgets = {
#            'description': Textarea(attrs={'cols':50, 'rows':5}),
#        }

#class CppComponentForm(ComponentForm):
#    class Meta:
#        model = CppComponent
#        fields = ['title', 'description']
#        widgets = {
#            'description': Textarea(attrs={'cols':50, 'rows':5}),
#        }

#class JavaComponentForm(ComponentForm):
#    class Meta:
#        model = JavaComponent
#        fields = ['title', 'description']
#        widgets = {
#            'description': Textarea(attrs={'cols':50, 'rows':5}),
#        }

#class PlainTextComponentForm(ComponentForm):
#    class Meta:
#        model = PlainTextComponent
#        fields = ['title', 'description', 'max_length']
#        widgets = {
#            'description': Textarea(attrs={'cols':50, 'rows':5}),
#            'max_length': TextInput(attrs={'style':'width:5em'}),
#        }


def filetype(fh):
    """
    Do some magic to guess the filetype.  Argument must be an open file-like object.
    """
    #TODO: replace with some real check
    if fh.name.endswith('.doc'):
        return "WORD"
    if fh.name.endswith('.odt'):
        return "OPENDOC"
    
    # methods extracted from the magic file (/usr/share/file/magic)
    # why not just check the filename?  Students seem to randomly rename.
    fh.seek(0)
    magic = fh.read(4)
    if magic=="PK\003\004" or magic=="PK00":
        return "ZIP"
    elif magic=="Rar!":
        return "RAR"
    elif magic[0:2]=="\037\213":
        fh.seek(0)
        gzfh = gzip.GzipFile(filename="filename", fileobj=fh)
        gzfh.seek(257)
        if gzfh.read(5)=="ustar":
            return "TGZ"
        else:
            return "GZIP"
    elif magic=="%PDF":
        return "PDF"
  
    fh.seek(257)
    if fh.read(5)=="ustar":
        return "TAR"

    return None


class SubmissionForm(ModelForm):
    # Set self.component to the corresponding Component object before doing validation.
    # e.g. "thisform.component = URLComponent.objects...."
    # This is automatically lhandled by make_form_from_list
    component = None
    class Meta:
        model = SubmittedComponent
        fields = []
        widgets = {}

    def check_size(self, upfile):
        """
        Check that file size is in allowed range.
        """
        if upfile.size / 1024 > self.component.max_size:
            return False
        return True

    def check_type(self, upfile):
        """
        Guess file type with magic, confirm that it matches file extension and is allowed for this submission type.
        """
        upfile.mode = "r" # not set in UploadedFile, so monkey-patch it in.
        ftype = filetype(upfile)
        
        # check that real file type is allowed
        allowed_types = self.instance.Type.Component.allowed_types
        if not ftype:
            raise forms.ValidationError('Unable to determine file type.  Allowed file types are: %s.' % (", ".join(allowed_types.keys())))
        if ftype not in allowed_types:
            raise forms.ValidationError('Incorrect file type.  File contents appear to be %s.  Allowed file types are: %s.' % (ftype, ", ".join(allowed_types.keys())))
        
        # check that extension matches
        extensions = allowed_types[ftype]
        if True not in [upfile.name.lower().endswith( e ) for e in extensions]:
            raise forms.ValidationError('File extension incorrect.  File appears to be %s data; allowed extensions are: %s.' % (ftype, ", ".join(extensions)))

    def check_is_empty(self, data):
        if data == None:
            return True
        if len(data) == 0:
            return True
        return False

    def check_filename(self, data):
        specified_filename = self.component.specified_filename.strip()
        if specified_filename and len(specified_name) > 0 and data.name != specified_filename:
            raise forms.ValidationError('File name incorrect.  It must be "%s".' % (specified_filename))
    
    def check_uploaded_data(self, data):
        if self.check_is_empty(data):
            raise forms.ValidationError("No file submitted.")
        self.check_type(data)
        self.check_filename(data)
        if not self.check_size(data):
            raise forms.ValidationError("File size exceeded max size, component can not be uploaded.")
        return data

#class SubmittedURLForm(SubmissionForm):
#    class Meta:
#        model = SubmittedURL
#        fields = ['url']
#        widgets = {
#            'url': TextInput(attrs={'style':'width:25em'}),
#        }
#    def clean_url(self):
#        url = self.cleaned_data['url']
#        if self.check_is_empty(url):
#            raise forms.ValidationError("No URL given.")
#        return url;

#class SubmittedArchiveForm(SubmissionForm):
#    class Meta:
#        model = SubmittedArchive
#        fields = ['archive']
#        widgets = {'archive': FileInput()}
#    def check_size(self, file):
#        if file.size / 1024 > self.component.max_size:
#            return False
#        return True
#    def clean_archive(self):
#        data = self.cleaned_data['archive']
#        if self.check_is_empty(data):
#            raise forms.ValidationError("No file submitted.")
#        if not self.check_type(data):
#            raise forms.ValidationError('File type incorrect.')
#        if not self.check_size(data):
#            raise forms.ValidationError("File size exceeded max size, component can not be uploaded.")
#        return data

#class SubmittedCppForm(SubmissionForm):
#    class Meta:
#        model = SubmittedCpp
#        fields = ['cpp']
#        widgets = {'cpp': FileInput()}
#    def clean_cpp(self):
#        data = self.cleaned_data['cpp']
#        if self.check_is_empty(data):
#            raise forms.ValidationError("No file submitted.")
#        if not self.check_type(data):
#            raise forms.ValidationError("File type incorrect.")
#        return data

#class SubmittedJavaForm(SubmissionForm):
#    class Meta:
#        model = SubmittedJava
#        fields = ['java']
#        widgets = {'java':FileInput()}
#    def clean_java(self):
#        data = self.cleaned_data['java']
#        if self.check_is_empty(data):
#            raise forms.ValidationError("No file submitted.")
#        if not self.check_type(data):
#            raise forms.ValidationError("File type incorrect.")
#        return data

#class SubmittedPlainTextForm(SubmissionForm):
#    class Meta:
#        model = SubmittedPlainText
#        fields = ['text']
#        widgets = {'text':Textarea(attrs = {'cols':50, 'rows':5})}
#    def check_length(self, text):
#        if len(text) > self.component.max_length:
#            return False
#        return True
#    def clean_text(self):
#        data = self.cleaned_data['text']
#        if self.check_is_empty(data):
#            raise forms.ValidationError("No text submitted.")
#        if not self.check_length(data):
#            raise forms.ValidationError("Text Length exceeded max length, text can not be uploaded.")
#        return data

def make_form_from_list(component_list, request=None):
    component_form_list = []
    for component in component_list:
        Type = component.Type
        if request:
            form = Type.SubmissionForm(request.POST, request.FILES, prefix=component.id)
        else:
            form = Type.SubmissionForm(prefix=component.id)
        form.component = component
        data = {'comp':component, 'form':form}
        component_form_list.append(data)
    return component_form_list

