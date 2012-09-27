from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms

class SmallTextField(FieldBase):

    class SmallTextConfigForm( FieldConfigForm ):
        min_length = forms.IntegerField( min_value=1, max_value=300 ) 
        max_length = forms.IntegerField( min_value=1, max_value=300 ) 

    def make_config_form(self):
        return SmallTextConfigForm(self.config)

    def make_entry_field(self):
        c = CharField(  required=bool(self.config['required']),
                        label=self.config['label'],
                        help_text=self.config['help_text'] )

        if self.config['min_length'] and int(self.config['min_length']) > 0:
            c.min_length = self.config['min_length'] 
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            c.max_length = self.config['max_length']
        return c
       
    def to_

class MediumTextFieldFactory(FieldType):
    pass
    
