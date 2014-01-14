from django.db import models
from django import forms
from django.forms.models import ModelForm
from django.forms.models import inlineformset_factory

from django_countries.countries import COUNTRIES

from models import ContinuousRule
from models import DiscreteRule
from models import GradeSource


class GradeSourceListForm(forms.Form):
    country = forms.ChoiceField(choices=COUNTRIES)


class GradeSourceForm(ModelForm):
    class Meta:
        model = GradeSource
        exclude = ("config",)


class DiscreteRuleForm(ModelForm):
    class Meta:
        model = DiscreteRule


class ContinuousRuleForm(ModelForm):
    class Meta:
        model = ContinuousRule


def rule_formset_factory(grade_source, reqpost=None):
    if grade_source.scale == 'DISC':
        DiscreteRuleFormSet = inlineformset_factory(GradeSource, DiscreteRule)
        formset = DiscreteRuleFormSet(reqpost, instance=grade_source)
    else:
        ContinuousRuleFormSet = inlineformset_factory(GradeSource, ContinuousRule)
        formset = ContinuousRuleFormSet(reqpost, instance=grade_source)

    return formset


class BaseGradeForm(forms.Form):
    name = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.grade_source = kwargs.pop('grade_source', None)
        super(BaseGradeForm, self).__init__(*args, **kwargs)
        self.initialize(self.grade_source)

    def clean_grade(self):
        grade = self.cleaned_data['grade']
        rule = self.grade_source.get_rule(grade)

        if rule:
            self.cleaned_data['rule'] = rule
            return grade
        else:
            raise forms.ValidationError('No rule found for grade')

    # Override these

    def initialize(self, grade_source):
        pass


class DiscreteGradeForm(BaseGradeForm):
    grade = forms.ChoiceField()

    def initialize(self, grade_source):
        values = grade_source.discrete_rules.values_list('lookup_value', flat=True)
        self.fields['grade'].choices = [('', '----')] + zip(values, values)


class ContinuousGradeForm(BaseGradeForm):
    grade = forms.DecimalField(max_digits=8, decimal_places=2)

    def initialize(self, grade_source):
        # TODO: Agree on min/max grade fields for GradeSource and limit the value of grade
        #       accordingly.
        pass
